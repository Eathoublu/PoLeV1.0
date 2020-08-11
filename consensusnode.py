# -*- coding: utf-8 -*-

# Demo for Pole V1.0  consensus node

import sys  
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QPushButton, QLabel, QLineEdit, QTextBrowser
from PyQt5.QtCore import *
import time
import random
import hashlib
import threading
import requests
from flask import *

class Worker(QThread):
    sinOut = pyqtSignal(str) 

    def __init__(self, parent=None):
        global app
        super(Worker, self).__init__(parent)
        self.app = app
        self.working = True
        self.port = -1
        self.addr = ''
        self.ipaddr = ''
        self.num = 0
        self.block = []
        self.node_list = []
        self.taskhashlist = []


        self.block_cache = []
        self.requestli_cache = []

    def __del__(self):
        self.working = False
        self.wait()

    def register(self):
        print('NODE LIST {}'.format(self.node_list))
        for ip in self.node_list:
            if ip == self.ipaddr:
                continue
            try:
                requests.post('{}/pole/protocol/addnode'.format(ip), json={'ipaddr':self.ipaddr, 'selfaddr': self.addr})
            except Exception as e:
                print('[E1]:{}'.format(e))

    def configargs(self, port, nodes, addr, blocks):
        self.port = port
        self.node_list = nodes
        self.addr = addr
        self.ipaddr = 'http://127.0.0.1:{}'.format(self.port)
        self.node_list.append(self.ipaddr)
        self.block = blocks
        self.register()


    def generate_block(self):
        if not self.requestli_cache:
            self.requestli_cache = [{'balance': 0, 'data': 'Default', 'model': None, 'addr': None, 'taskhash': None}]
        self_block = {'acc': self.getNouce(), 'timestamp':time.time(), 'addr': self.addr, 'donetask': self.requestli_cache[0], 'body':{'msg': self.requestli_cache}}
        self.block_cache.append(self_block)
        self.broadcast(self_block)
        pass

    def broadcast(self, selfblock):
        for ip in self.node_list:
            if ip == self.ipaddr:
                continue
            try:
                requests.post('{}/pole/protocol/consensus'.format(ip), json=selfblock)
            except Exception as e:
                print('[E2]:{}'.format(e))
        return

    def get_winner(self):
        print('BLOCK CACHE: {}'.format(self.block_cache))
        if not self.block_cache:
            return
        maxacc = -1
        winner_addr = ''
        bidx = None
        for idx in range(len(self.block_cache)):
            print('SEE', idx, self.block_cache[idx]['acc'], maxacc)
            if self.block_cache[idx]['acc'] > maxacc:
                maxacc = self.block_cache[idx]['acc']
                winner_addr = self.block_cache[idx]['addr']
                bidx = idx

        if winner_addr == self.addr:
            print('[Winner]:{}'.format(self.block_cache[bidx]))
            self.sinOut.emit('TOKENS:{}'.format(self.block_cache[bidx]['body']['msg'][0]['balance']))
        if len(self.requestli_cache) >= 1:
            self.requestli_cache = self.block_cache[bidx]['body']['msg'][1:]
        else:
            self.requestli_cache = [{'balance': 0, 'data': 'Default', 'model': None, 'addr': None, 'taskhash': None}]
        self.block.append(self.block_cache[bidx])
        self.block_cache = []
        self.sinOut.emit('4')
        time.sleep(1)
        return

    def getNouce(self):
        return random.random()

    def run(self):
        app = Flask(__name__)

        @app.route('/')
        def index():
            return '<h1>Welcome using PoLe Demo</h1>', 200

        @app.route('/pole/protocol/V1')
        def protocol():
            return jsonify({'port': self.port, 'status': 'working', 'addr': self.addr, 'msg':200, 'nodes': self.node_list, 'blocks': self.block}), 200

        @app.route('/pole/protocol/addnode', methods=['POST'])
        def add_node():
            self.sinOut.emit('1')
            jsondata = json.loads(request.get_data())
            self.node_list.append('{}'.format(jsondata['ipaddr']))
            return jsonify({'msg': 200}), 200

        @app.route('/get-request', methods=['POST'])
        def get_request():
            self.sinOut.emit('2')
            datanoderequest = json.loads(request.get_data())
            taskhash = datanoderequest['taskhash']
            if taskhash in self.taskhashlist:
                return jsonify({'msg': 200}), 200
            self.requestli_cache.append(datanoderequest)
            self.taskhashlist.append(taskhash)
            t1 = threading.Thread(target=broadcastinvf, args=(self.node_list, datanoderequest, self.ipaddr))
            t1.start()

            return jsonify({'msg': 200}), 200

        def broadcastinvf(nodelist, requestdata, selfip):
            for ip in nodelist:
                try:
                    if ip == selfip:
                        continue
                    requests.post('{}/get-request'.format(ip), json=requestdata)
                except Exception as e:
                    print('[E4]:{}'.format(e))

        @app.route('/explore')
        def explore():
            return jsonify(self.block), 200

        @app.route('/pole/protocol/consensus', methods=['POST'])
        def consensus():
            self.sinOut.emit('3')
            self.block_cache.append(json.loads(request.get_data()))
            return jsonify({'msg': 200}), 200

        @app.route('/datanode/ifdone/<taskhash>', methods=['GET'])
        def datanoderequest(taskhash):
            for idx in range(len(self.block)-1, 0, -1):
                if self.block[idx]['donetask']['taskhash'] == taskhash:
                    return jsonify({'code': 200, 'blockidx': idx, 'msg': 'task is done', 'hash': taskhash, 'content': '<Model><Weight></Weight></Model>'}), 200
            return jsonify({'code': 500, 'msg': 'task wait in queue.'})

        app.run(port=self.port, threaded=True)


class FirstUi(QMainWindow): 
    def __init__(self, port, extnodeli, extblockli):
        super(FirstUi, self).__init__()
        self._echo = ''
        self._count = 2253
        self.r = None
        self.b = 1000
        self.language = 0
        self.port = port
        self.extnodeli = extnodeli
        self.thread = Worker()
        r = hashlib.sha256(bytes(str(random.random()), encoding='utf8')).hexdigest()
        print('self addr: {}'.format(r))
        self.r = r
        self.thread.sinOut.connect(self.interrupt1)
        self.thread.configargs(port=self.port, addr=r, nodes=extnodeli, blocks=extblockli)
        self.thread.start()
        self.c1 = 20
        self.c2 = 10
        self.countdown1 = self.c1 
        self.countdown2 = self.c2 

        self.init_ui()

    def init_ui(self):

        self.resize(800, 400)  
        self.setWindowTitle('Consensus Node') 

        self.lable1 = QLabel('<h1>PoLe Demo</h1>', self)
        self.lable1.setGeometry(330, 20, 300, 25)

        self.lable3 = QLabel('<h2>Consensus Node</h2>', self)
        self.lable3.setGeometry(320, 50, 300, 25)

        self.lable4 = QLabel('IP : http://127.0.0.1:{}'.format(self.port), self)
        self.lable4.setGeometry(550, 15, 300, 25)

        self.lable5 = QLabel('Console:', self)
        self.lable5.setGeometry(240, 70, 300, 25)

        self.lable6 = QLabel('<h2>Balance:</h2>', self)
        self.lable6.setGeometry(30, 50, 300, 25)

        self.lable7 = QLabel('<h2>Address:</h2>', self)
        self.lable7.setGeometry(30, 200, 300, 25)

        self.lable8 = QLabel('<h1>{}</h1>'.format(self.b), self)
        self.lable8.setGeometry(30, 90, 300, 25)

        self.lable9 = QLabel('<h1>{}</h1>'.format(self.r[:10]), self)
        self.lable9.setGeometry(30, 240, 300, 25)

        self.lable10 = QLabel('<h2>Status:</h2>', self)
        self.lable10.setGeometry(30, 320, 300, 25)

        self.lable11 = QLabel('<h1>Working</h1>', self)
        self.lable11.setGeometry(30, 340, 300, 50)

        self._echo = """        Event                |   Entity  |       Time       |  IP Addr
-----------------------------------------------------------------------    
        """

        self.tb = QTextBrowser(self)
        self.tb.setText(self._echo)
        self.tb.setGeometry(240, 100, 500, 220)

        self.btn5 = QPushButton('Refresh', self)  
        self.btn5.setGeometry(320, 320, 100, 25)  
        self.btn5.clicked.connect(self.slot_btn_function)  

        self.lable2 = QLabel('Status: Collecting Requests...', self)
        self.lable2.setGeometry(450, 320, 300, 25)

        self.btn6 = QPushButton('ZH/EN', self)
        self.btn6.setGeometry(10, 10, 70, 25)
        self.btn6.clicked.connect(self.changeLanguage)

        self.timer = QBasicTimer()  
        self.timer.start(1000, self)



    def slot_btn_function(self):

        pass

    def timerEvent(self, event):
        if event.timerId() == self.timer.timerId():

            if self.countdown1 == 0:
                self.countdown1 = self.c1
                self.thread.get_winner()
                self.lable2.setText("Status: Collecting Requests...")
            else:
                self.countdown1 -= 1

            if self.countdown2 == 0:
                self.countdown2 = self.c2
                self.thread.generate_block()
                self.append_echo('Start training model.')
                self.lable2.setText("Status: Training Models...")
            else:
                self.countdown2 -= 1





    def changeLanguage(self):

        if self.language == 1:
            self.language = 0
            self.lable1.setText('<h1>PoLe Demo</h1>')
            self.lable3.setText('<h2>Consensus Node</h2>')
            self.lable4.setText('IP : http://127.0.0.1:{}'.format(self.port))
            self.lable5.setText('Console:')
            self.lable6.setText('<h2>Balance:</h2>')
            self.lable7.setText('<h2>Address:</h2>')
            self.lable10.setText('<h2>Status:</h2>')
            self.lable11.setText('<h1>Working</h1>')

            self.btn5.setText('refresh')

        elif self.language == 0:
            self.language = 1
            self.lable1.setText('<h2>PoLe 示例</h2>')
            self.lable3.setText('<h2>共识节点</h2>')
            self.lable4.setText('IP地址 : http://127.0.0.1:{}'.format(self.port))
            self.lable5.setText('控制台:')
            self.lable6.setText('<h2>余额:</h2>')
            self.lable7.setText('<h2>地址:</h2>')
            self.lable10.setText('<h2>状态:</h2>')
            self.lable11.setText('<h1>正在工作</h1>')

            self.btn5.setText('刷新')

    def append_echo(self, msg):

        self._echo += """{}      | {}|  {} |  127.0.0.1:{}
-----------------------------------------------------------------------
        """.format(msg, hashlib.md5(bytes(msg+str(time.time()), encoding='utf8')).hexdigest()[:10], time.time(), self.port)
        self.tb.setText(self._echo)

    def interrupt1(self, sig):
        if sig == '1':
            self.append_echo('A new node registered.')

        if sig == '2':
            self.append_echo('Receive new request.')

        if sig == '3':
            self.append_echo('Received new block.')

        if sig == '4':
            self.append_echo('Consensus reached.')
            self.lable2.setText("Status: Collecting Requests...")


        if 'TOKENS' in sig:
            self.append_echo('Became winner.')
            fee = str(sig)
            print('[FEE]:{}'.format(fee))
            self.lable8.setText("<h1>{}</h1>".format(self.b + int(fee.split(':')[-1])))
            print('[NOW FEE]:{}'.format(self.b + int(fee.split(':')[-1])))
            self.b += int(fee.split(':')[-1])

def get_a_port():
    originp = 7000
    FLAG = True
    nodelist = []
    blocklist = []

    while FLAG:
        try:
            req = requests.get('http://127.0.0.1:{}/pole/protocol/V1'.format(originp))
            jsondata = json.loads(req.content)
            nodelist = jsondata['nodes']
            blocklist = jsondata['blocks']
            originp += 1
        except:

            FLAG = False

    return originp, nodelist, blocklist


if __name__ == '__main__': 

    appmain = QApplication(sys.argv)
    w = FirstUi(*get_a_port())  # 将第一和窗口换个名字
    w.show()  # 将第一和窗口换个名字显示出来
    sys.exit(appmain.exec_())  # app.exet_()是指程序一直循环运行直到主窗口被关闭终止进程（如果没有这句话，程序运行时会一闪而过）
