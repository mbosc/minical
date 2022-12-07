import telegram
import yaml

class pyHerald:
    
    def __init__(self, channel=0):
        self.channel = channel
        with open('secrets.yaml') as f:
            self.secrets = yaml.safe_load(f)
        self.tokens = [self.secrets['teletoken']]
        self.chats = [self.secrets['chatid']]
        self.bot = telegram.Bot(self.tokens[self.channel])
        
    def sendMsg(self, text):
        for chat in self.chats:
            self.bot.send_message(chat, text)

    def sendPic(self, img, text=None):
        if not isinstance(img, str):
            import cv2
            cv2.imwrite('temp.png', img)
            img = 'temp.png'
        self.bot.send_photo(self.chats[0], open(img, 'rb'), caption=text)

    @staticmethod
    def oneshotmessage(msg):
        m = pyHerald()
        m.sendMsg(msg)
        del(m)
    
    @staticmethod
    def oneshotpic(img, text=None):
        m = pyHerald()
        m.sendPic(img, text)
        del(m)

if __name__ == '__main__':

    import sys
    pyHerald.oneshotmessage(' '.join(sys.argv[1:]))