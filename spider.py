# -*- coding:utf-8 -*-
import urllib2
import time
import requests
import urllib
import re
import cookielib
import sys
import datetime, time
from bs4 import BeautifulSoup


email = 'xxx@xx.com'  # 账号
password = 'xxxxx'  # 密码


# 豆瓣爬虫类
class DoubanSpider(object):
    def __init__(self, movie_id, timestamp, rank,  start=0):
        self.email = email
        self.password = password
        self.data = {
                "form_email": email,
                "form_password": password,
                "source": "index_nav",
                "remember": "on"
        }

        self.login_url = 'http://www.douban.com/accounts/login'
        self.load_cookies()
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookie))
        self.opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.116 Safari/537.36')]
        self._start_time = time.time()
        # movie id
        self._movie_id = str(movie_id)
        self.timestamp = timestamp
        self.start_ts = timestamp - 3600 * 24 * 7
        self.end_ts = timestamp + 3600 * 24 * 30
        self.rank = rank
        # 评论起始index
        self._next_index = str(start)
        # 下次抓取的地址
        self._next_url = None
        self.set_next_url()

    def load_cookies(self):
        try:
            self.cookie = cookielib.MozillaCookieJar('Cookies.txt')
            self.cookie.load('Cookies_saved.txt')
            print "loading cookies.."
        except:
            print "The cookies file is not exist."
            self.login_douban()
            # reload the cookies.
            self.load_cookies()

    # login douban and save the cookies into file.
    def login_douban(self):
        cookieFile = "Cookies_saved.txt"
        cookieJar = cookielib.MozillaCookieJar(cookieFile)
        # will create (and save to) new cookie file
        # cookieJar.save();

        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookieJar))
        opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.116 Safari/537.36')]
        # !!! following urllib2 will auto handle cookies
        response = opener.open(self.login_url, urllib.urlencode(self.data), timeout=1000)
        html = response.read()

        # fp = open("1.html","wb")
        # fp.write(html)
        # fp.close

        imgurl = re.compile(r'<img id="captcha_image" src="(.+?)" alt="captcha"').findall(html)
        if imgurl:
            # download the captcha_image file.
            # urllib.urlretrieve(imgurl[0], 'captcha.jpg')
            print "the captcha_image address is %s" %imgurl[0]
            data = opener.open(imgurl[0]).read()
            f = file("captcha.jpg", "wb")
            f.write(data)
            f.close()

            captcha = re.search('<input type="hidden" name="captcha-id" value="(.+?)"/>', html)
            if captcha:
                vcode=raw_input('图片上的验证码是：')
                self.data["captcha-solution"] = vcode
                self.data["captcha-id"] = captcha.group(1)
                self.data["user_login"] = "登录"
                # 验证码验证
                response = opener.open(self.login_url, urllib.urlencode(self.data),  timeout = 1000)
        # 登录成功
        if response.geturl() == "http://www.douban.com/":
            print 'login success !'
            # update cookies, save cookies into file
            cookieJar.save()
            self.opener = opener
        else:
            return False
        return True

    def set_next_url(self):
        self._next_url = 'http://movie.douban.com/subject/' + self._movie_id + '/comments?start=' + self._next_index +'&limit=20&sort=new_score'

    def get_content(self):
        try:
            # request = urllib2.Request(self._next_url)
            response = self.opener.open(self._next_url, timeout=10000)
            content = response.read().decode('utf-8')
            return content
        except urllib2.URLError, e:
            if hasattr(e, "code"):
                print e.code
            if hasattr(e, "reason"):
                print e.reason

    def run(self):
        print "开始爬........"
        page = 0
        filename = "./" + self.rank + ".txt"
        save_file = open(filename, "w")
        while self._next_index:
            s_time = time.time()
            try:
                content = self.get_content()
                soup = BeautifulSoup(content)
                pattern = re.compile('.*?allstar(.*?)rating.*?<span class="">(.*?)</span>*?', re.S)
                comments_str = soup.findAll('span', class_="comment-info")
                items =filter(lambda y: len(y)!=0, map(lambda x: re.findall(pattern, str(x)), comments_str))
            except:
                break
            if len(items) == 0:
                break
            for item in items:
                star = item[0][0].strip()
                date = item[0][1].strip()
                ts = to_timestamp(date, "%Y-%m-%d")
                if self.start_ts <= ts <= self.end_ts:
                    try:
                        comments = '\t'.join([star, date]).encode('utf-8') + '\n'
                        save_file.write(comments)
                    except:
                        pass
            indexs = soup.findAll('a', class_="next")
            if len(indexs) != 0:
                next_pattern = re.compile('.*?start=(.*?)&amp.*?', re.S)
                index = re.findall(next_pattern, str(indexs[0]))
            else:
                break
            if len(index) != 0 and index[0] != self._next_index:
                self._next_index = index[0]
                self.set_next_url()
                time.sleep(1.2)
                if page%300==0 and page!=0:
                    time.sleep(181)
            else:
                self._next_index = None
            page += 1
            e_time = time.time()
            print "爬了", page, "页, 耗时=", e_time - s_time, "秒,  index=", self._next_index, "程序运行=", time.time() - self._start_time
        save_file.close()
        print self._movie_id, "抓取完毕!"


def to_timestamp(date, str_type="%Y/%m/%d"):
    dt = datetime.datetime.strptime(date, str_type)
    return time.mktime(dt.timetuple())


def get_movie_info(filename):
    movie_dict = dict()
    with open(filename) as f:
        for line in f.readlines():
            rank, date, mid = line.strip().split(',')
            timestamp = to_timestamp(date)
            movie_dict[mid] = [timestamp, rank]
    f.close()
    return movie_dict


if __name__ == "__main__":
    movies_dict = get_movie_info(sys.argv[1])
    for mid, v in movies_dict.items():
        m_timestamp, m_rank = v
        loginUrl = 'http://accounts.douban.com/login'
        formData={
            "redir": "http://movie.douban.com/mine?status=collect",
            "form_email": email,
            "form_password": password,
            "login": u'登录'
        }
        headers = {"User-Agent": 'Mozilla/5.0 (Windows NT 6.1)\
         AppleWebKit/537.36 (KHTML, like Gecko) Chrome/43.0.2357.134 Safari/537.36'}
        r = requests.post(loginUrl, data=formData, headers=headers)
        mv = DoubanSpider(mid, m_timestamp, m_rank)
        mv.run()
