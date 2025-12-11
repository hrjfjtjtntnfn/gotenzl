import time
import requests
import json
import urllib.parse
import base64
from Crypto.Cipher import AES

class GotenZL:
    def __init__(self, imei, _cookies , ojb): 
        self.ojb = ojb
        self.imei = imei
        self._cookies = _cookies
        self._session = requests.Session()
        self._config = None
        self.isRun = True
        self._headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "sec-ch-ua": "\"Not-A.Brand\";v=\"99\", \"Chromium\";v=\"124\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Linux\"",
            "origin": "https://chat.zalo.me",
            "sec-fetch-site": "same-site",
            "sec-fetch-mode": "cors",
            "sec-fetch-dest": "empty",
            "referer": "https://chat.zalo.me/",
            "accept-language": "vi-VN,vi;q=0.9,fr-FR;q=0.8,fr;q=0.7,en-US;q=0.6,en;q=0.5",
        }

    def _pad(self, s, block_size):
        try:
            padding_length = block_size - len(s) % block_size
            return s + bytes([padding_length]) * padding_length
        except:
            return s

    def _unpad(self, s, block_size):
        try:
            padding_length = s[-1]
            return s[:-padding_length]
        except:
            return s

    def _encode(self, params):
        try:
            key = base64.b64decode(self._config['secret_key'])
            iv = bytes.fromhex("00000000000000000000000000000000")
            cipher = AES.new(key, AES.MODE_CBC, iv)
            plaintext = json.dumps(params).encode()
            padded_plaintext = self._pad(plaintext, AES.block_size)
            ciphertext = cipher.encrypt(padded_plaintext)
            return base64.b64encode(ciphertext).decode()
        except:
            return "{}"

    def _decode(self, params):
        try:
            params = urllib.parse.unquote(params)
            key = base64.b64decode(self._config['secret_key'])
            iv = bytes.fromhex("00000000000000000000000000000000")
            cipher = AES.new(key, AES.MODE_CBC, iv)
            ciphertext = base64.b64decode(params.encode())
            padded_plaintext = cipher.decrypt(ciphertext)
            plaintext = self._unpad(padded_plaintext, AES.block_size)
            plaintext = plaintext.decode("utf-8")
            return json.loads(plaintext)
        except:
            return None

    def _get(self, *args, **kwargs):
        try:
            return self._session.get(*args, **kwargs, headers=self._headers, cookies=self._cookies, timeout=15)
        except:
            return None

    def _post(self, *args, **kwargs):
        try:
            return self._session.post(*args, **kwargs, headers=self._headers, cookies=self._cookies, timeout=15)
        except:
            return None

    def login(self):
        try:
            if not self._cookies:
                return False

            params = {
                "imei": self.imei,
                "computer_name": "Web",
                "ts": int(time.time() * 1000),
                "netry": 0
            }
            response = self._get("https://wpa.chat.zalo.me/api/login/getLoginInfo", params=params)
            if not response or response.status_code != 200:
                return False

            data = response.json()
            if data.get("error_code") == 0:
                self._config = {
                    "send2me_id": data['data']['send2me_id'],
                    "secret_key": data['data']['zpw_enk']
                }
                return True
            else:
                return False
        except:
            return False

    def getLastMsgs(self):
        try:
            params = {
                "zpw_ver": "634",
                "zpw_type": "30",
                "params": self._encode({
                    "threadIdLocalMsgId": json.dumps({}),
                    "imei": self.imei
                })
            }
            response = self._get("https://tt-convers-wpa.chat.zalo.me/api/preloadconvers/get-last-msgs", params=params)
            if not response or response.status_code != 200:
                return {"data": {"msgs": [], "groupMsgs": []}}

            data = response.json()
            
            if data.get("data"):
                results = self._decode(data['data'])
                return results or {"data": {"msgs": [], "groupMsgs": []}}
            return {"data": {"msgs": [], "groupMsgs": []}}
        except:
            return {"data": {"msgs": [], "groupMsgs": []}}

    def sendMessage(self, message, thread_id, thread_type, tls=0):
        try:
            params = {
                "zpw_ver": 645,
                "zpw_type": 30,
                "nretry": 0
            }

            payload = {
                "params": {
                    "message": message,
                    "clientId": int(time.time() * 1000),
                    "imei": self.imei,
                    "ttl": tls,
                }
            }

            if thread_type == 0:  # tin nhắn cá nhân
                url = "https://tt-chat2-wpa.chat.zalo.me/api/message/sms"
                payload["params"]["toid"] = str(thread_id)
            elif thread_type == 1:  # tin nhắn nhóm
                url = "https://tt-group-wpa.chat.zalo.me/api/group/sendmsg"
                payload["params"]["visibility"] = 0
                payload["params"]["grid"] = str(thread_id)
            else:
                return False

            payload["params"] = self._encode(payload["params"])
            response = self._post(url, params=params, data=payload)
            if response:
                data = response.json()
                return data.get("error_code") == 0
            return False
        except:
            return False

    def _listen(self):
        HasRead = set()
        while self.isRun:
            try:
                if len(HasRead) > 100000:
                    HasRead.clear()

                ListenTime = int((time.time() - 15) * 1000)
                messages = self.getLastMsgs()
                msgs = messages.get('data', {}).get('msgs', [])
                groupmsgs = messages.get('data', {}).get('groupMsgs', [])

                for message in msgs:
                    try:
                        ts = int(message.get("ts", 0))
                        msg_id = message.get("msgId")
                        if ts >= ListenTime and msg_id and msg_id not in HasRead:
                            HasRead.add(msg_id)
                            author = str(int(message.get('uidFrom') or 0) or self._config.get('send2me_id', '0'))
                            content = message.get('content', '')
                            thread = str(int(message.get('uidTo') or message.get('idTo') or 0))
                            self.ojb.onMessage(msg_id, author, content, message, thread, 0)
                    except:
                        pass

                for message in groupmsgs:
                    try:
                        ts = int(message.get("ts", 0))
                        msg_id = message.get("msgId")
                        if ts >= ListenTime and msg_id and msg_id not in HasRead:
                            HasRead.add(msg_id)
                            author = str(int(message.get('uidFrom') or 0) or self._config.get('send2me_id', '0'))
                            content = message.get('content', '')
                            thread = str(message.get('idTo') or self._config.get('send2me_id', '0'))
                            self.ojb.onMessage(msg_id, author, content, message, thread, 1)
                    except:
                        pass

                time.sleep(3)
            except:
                time.sleep(5)
                continue
