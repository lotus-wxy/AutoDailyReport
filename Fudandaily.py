import time
import logging
import yagmail
from json import loads as json_loads
from os import path as os_path
from sys import exit as sys_exit
from os import environ
from lxml import etree
from requests import session

class FduLogin:
    """
    建立与复旦服务器的会话，执行登录/登出操作
    _page_init()
    login()
    logout()
    close()
    sendmail()
    """
    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:76.0) Gecko/20100101 Firefox/76.0"

    def __init__(self, user_info, url_login):
        """
        初始化session，及登录信息
        :user_info: 包含学号密码及收信邮箱
        :login_url: 登录页
        """
        self.session = session()
        self.session.headers['User-Agent'] = self.UA
        self.url_login = url_login

        self.username = user_info[0]
        self.password = user_info[1]
        self.email = user_info[2]
        self.mail_title = ""
        self.mail_content = ""

    def _page_init(self):
        """
        检查是否能打开登录页面
        :return: 登录页page source
        """
        #print("◉Initiating——", end='')
        page_login = self.session.get(self.url_login)

        #print("return status code",page_login.status_code)

        if page_login.status_code == 200:
            #print("◉Initiated——", end="")
            info_str = "Initial Sccuess! "
            #self.mail_content += info_str + '\n'
            logger.info("%s",info_str)
            return page_login.text
        else:
            info_str = "Fail to open Login Page, Check your Internet connection!"
            self.mail_content += info_str + '\n'
            logger.error("%s",info_str)
            self.close()

    def login(self):
        """
        执行登录
        """

        card_info = "正在为" + self.username + "打卡"
        self.mail_content += card_info + '\n'
        page_login = self._page_init()

        #print("parsing Login page——", end="")
        html = etree.HTML(page_login, etree.HTMLParser())

        #print("getting tokens")
        data = {
            "username": self.username,
            "password": self.password,
            "service" : "https://zlapp.fudan.edu.cn/site/ncov/fudanDaily"
        }

        # 获取登录页上的令牌
        data.update(
                zip(
                        html.xpath("/html/body/form/input/@name"),
                        html.xpath("/html/body/form/input/@value")
                )
        )

        headers = {
            "Host"      : "uis.fudan.edu.cn",
            "Origin"    : "https://uis.fudan.edu.cn",
            "Referer"   : self.url_login,
            "User-Agent": self.UA
        }

        #print("◉Login ing——", end="")
        post = self.session.post(
                self.url_login,
                data=data,
                headers=headers,
                allow_redirects=False)

        #print("return status code", post.status_code)

        if post.status_code == 302:
            #print("\n***********************"
            #      "\n◉登录成功"
            #      "\n***********************\n")
            info_str = "登录成功" 
            self.mail_content += info_str + '\n'
            logger.info("%s", info_str)
        else:
            #print("◉登录失败，请检查账号信息")
            info_str = "login failed, check your account info "
            self.mail_content += info_str + '\n'
            self.mail_title += '[ERROR]'
            logger.error("%s", info_str)
            self.close()
        
    def logout(self):
        """
        执行登出
        """
        exit_url = 'https://uis.fudan.edu.cn/authserver/logout?service=/authserver/login'
        expire = self.session.get(exit_url).headers.get('Set-Cookie')
        # print(expire)

        if '01-Jan-1970' in expire:
            #print("◉登出完毕")
            info_str = "登出完毕"
            self.mail_content += info_str + '\n'
            logger.info("%s", info_str)
        else:
            #print("◉登出异常")
            info_str = "登出异常"
            self.mail_content += info_str + '\n'
            logger.error("%s", info_str)

    def close(self):
        """
        执行登出并关闭会话
        """
        self.logout()
        self.session.close()
        logger.info("session closed")
        #print("◉关闭会话")
        #print("************************")
        #input("回车键退出")
        #sys_exit()

    def sendmail(self):
        dailymail = yagmail.SMTP(
                                user='fdureporter@163.com',
                                password='WRSREHPSHPMOXCWM',
                                host='smtp.163.com'
                                )

        to = [self.email]
   ##     with open("./res.txt", 'r') as f:
    #        tmp = f.read()
        mail_cont = [self.mail_content]

        logger.info("Sending mail to usr %s",self.username)

        dailymail.send( to=to, subject = self.mail_title + "平安复日", contents = mail_cont)

class AutoReport(FduLogin):
    last_info = ''

    def get_lastinfo(self):
        """
        获取用户上次填报的信息
        """
        get_info = self.session.get('https://zlapp.fudan.edu.cn/ncov/wap/fudan/get-info')
        self.last_info = get_info.json()["d"]["info"]
        self.last_info_date = self.last_info["date"]
        self.last_info_position = json_loads(self.last_info['geo_api_info'])['addressComponent']

    def report(self):
        """
        自动填写平安复日
        """
        headers = {
            "Host"      : "zlapp.fudan.edu.cn",
            "Referer"   : "https://zlapp.fudan.edu.cn/site/ncov/fudanDaily?from=history",
            "DNT"       : "1",
            "TE"        : "Trailers",
            "User-Agent": self.UA
        }

        logger.info("Posting...")
        self.mail_content += "正在提交..." + '\n'

        province = self.last_info_position.get("province", "")
        print(province)
        city = self.last_info_position.get("city", "")
        print(city)
        if not city: city = province

        district = self.last_info_position.get("district", "")
        print(district)
        self.last_info.update(
                {
                    "tw"      : "13",
                    "province": province,
                    "city"    : city,
                    "district": district,
                    "area"    : " ".join((province, city, district))
                }
        )

        save = self.session.post(
                'https://zlapp.fudan.edu.cn/ncov/wap/fudan/save',
                data=self.last_info,
                headers=headers,
                allow_redirects=False)

        save_msg = json_loads(save.text)["m"]
        #print(save_msg, '\n\n')
        logger.info("%s",save_msg)
        self.mail_content += save_msg + '\n'

    def check(self):
        """
        检查今天是否已提交平安复旦
        """
        self.get_lastinfo()
        logger.info("%s", self.last_info_date)
        logger.info("%s", self.last_info_position)

        today = time.strftime("%Y%m%d", time.localtime())

        if False:   #self.last_info["date"] == today
            info_str = "今日已提交"
            self.mail_title += '[已提交]'
            self.mail_content += info_str + '\n'
            logger.info("%s",info_str)
        else:
            info_str = "今日尚未提交"
            self.mail_content += info_str + '\n'
            logger.info("%s \n",info_str)
            self.report()
            self.get_lastinfo()
            self.mail_title += '[填报成功]'
            cur_info_str = "Current Post record is " + self.last_info_date
            logger.info("%s",cur_info_str)

def get_account():
    
    USERNAME = environ['USERNAME']
    PASSWORD = environ['PASSWORD']
    EMAIL = environ['EMAIL']
    user_info = [USERNAME, PASSWORD, EMAIL]
    return user_info

if __name__ == '__main__':

    """
    设置log格式
    """
    logging.basicConfig(filename = 'daily.log',level = logging.INFO, format = '%(asctime)s - %(funcName)s - %(lineno)d - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)

    """
    获取用户名密码及邮箱
    """
    user_info = get_account()

    url_login = 'https://uis.fudan.edu.cn/authserver/login?' \
                  'service=https://zlapp.fudan.edu.cn/site/ncov/fudanDaily'
    daily_fudan = AutoReport(user_info, url_login)
    logger.info("PingAnFuDan for user: %s \n",user_info[0])
    daily_fudan.login()
    daily_fudan.check()
    daily_fudan.close()
    daily_fudan.sendmail()
