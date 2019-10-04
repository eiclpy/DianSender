# -+- coding=utf8 -+-
import base64
import copy
import json
import smtplib
import time
from email.header import Header
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formataddr
from config import getHostSetting


def make_mail(setting):
    data = MIMEMultipart()
    data['From'] = formataddr(
        (Header(setting['nickname'], 'utf-8').encode(), setting['user']))
    data['To'] = ''
    data['Subject'] = Header(setting['subject'], 'utf-8').encode()
    data.attach(MIMEText(setting['context'], 'plain', 'utf-8'))
    for fname, val in setting['attachments'].items():
        part = MIMEApplication(base64.b64decode(
            val.split(',')[-1]))
        part.add_header('Content-Disposition', 'attachment',
                        filename='=?UTF-8?B?' + base64.b64encode(fname.encode('utf-8')).decode('utf-8') + '?=')
        data.attach(part)
    return data


class Server:
    def __init__(self, settingfile):
        self.settingfilebase = settingfile.replace('.json', '')
        with open(settingfile, 'r') as fp:
            self.setting = json.load(fp)
        self.flog = open(self.settingfilebase+'_log.log', 'w')
        self.username = self.setting['user']
        self.password = self.setting['passwd']
        self.debug = self.setting['debugMode']
        self.hostSetting = getHostSetting(self.username)

        self.fail_send = []
        self.all_send = []
        self.total_send = 0

        self._login = False

    def print(self, *args, **kw):
        print(*args, **kw, file=self.flog)
        self.flog.flush()
        print(*args, **kw)

    def log_error(self):
        if self.fail_send:
            with open(self.settingfilebase+'_fail.json', 'r') as fp:
                json.dump(self.fail_send, fp)

    def save_last_successful_send(self):
        with open(self.settingfilebase+'_success.json', 'w') as fp:
            json.dump([x for x in self.all_send if not x in self.fail_send], fp)

    def stls(self):
        """Start TLS."""
        self.server.ehlo()
        self.server.starttls()
        self.server.ehlo()

    def login(self):
        """Login"""
        if self.debug:
            self._login = True
            self.print('Login successful (DEBUG MODE)')
            return True
        try:
            self.server = smtplib.SMTP(self.hostSetting['host'], self.hostSetting['port'])
        except:
            self.print('无法连接服务器，请检查网络是否连通')
            return False

        if self._login:
            self.print('duplicate login!')
            return True

        self.stls()

        try:
            self.server.login(self.username, self.password)
        except smtplib.SMTPAuthenticationError:
            self.print('username or password error')
            return False

        self._login = True
        self.print('Login successful')
        return True

    def logout(self):
        """Logout"""
        if self.debug:
            self._login = False
            self.server = None
            self.print('Logout successful (DEBUG MODE)')
            return

        if not self._login:
            self.print('Logout before login!')
            return

        try:
            code, message = self.server.docmd("QUIT")
            if code != 221:
                raise smtplib.SMTPResponseException(code, message)
        except smtplib.SMTPServerDisconnected:
            pass
        finally:
            self.server.close()

        self.server = None
        self._login = False
        self.print('Logout successful')

    def check_available(self) -> bool:
        """test server"""
        try:
            self.login()
            self.logout()
            return True
        except:
            self.print('server does not available')
            return False

    def is_login(self) -> bool:
        return self._login

    def _send_mails(self, reciver, msg):
        if not self.is_login():
            self.login()
        msg['Bcc'] = COMMASPACE.join(reciver)
        msg = msg.as_string()
        self.print('发送给%d人 ' % len(reciver), reciver)
        ret = None
        try:
            if self.debug:
                self.print('(DEBUG MODE)Send to %d' % len(reciver))
            else:
                ret = self.server.sendmail(
                    self.username, reciver, msg)
        except Exception as e:
            self.print(e)
            self.fail_send.extend(reciver)

        self.all_send.extend(reciver)
        self.total_send += len(reciver)
        if ret:
            self.fail_send.extend(ret.keys())
        self.print('==========当前总发送数====== ', self.total_send)

    def send_all_mails(self):
        reciver = self.setting['emails']
        last = len(reciver)
        msg = make_mail(self.setting)
        if not self.is_login():
            self.login()
        send_index = 0
        counter = 0
        login_cnt = 1
        while last > 0:
            if last >= self.hostSetting['mails_per_send']:
                self._send_mails(
                    reciver[send_index:send_index+self.hostSetting['mails_per_send']], copy.deepcopy(msg))
                send_index += self.hostSetting['mails_per_send']
                counter += self.hostSetting['mails_per_send']
                last -= self.hostSetting['mails_per_send']
            elif last > 0:
                self._send_mails(reciver[send_index:], copy.deepcopy(msg))
                send_index += last
                counter += last
                last = 0

            if last > 0 and counter+self.hostSetting['mails_per_send'] > self.hostSetting['mails_per_login']:
                self.print('Relogin')
                self.logout()
                if last > 0 and login_cnt > self.hostSetting['reset_per_n_login']:
                    login_cnt = 0
                    self.print('Interval')
                    if not self.debug:
                        time.sleep(self.hostSetting['reset_interval'])
                else:
                    if not self.debug:
                        time.sleep(self.hostSetting['interval_between_login'])
                self.login()
                counter = 0
                login_cnt += 1

            yield int((1.0-last/len(reciver))*100)
        self.logout()
        self.print('Finish send')
        self.log_error()
        self.save_last_successful_send()
