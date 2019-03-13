import asyncio
import uvloop
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

import argparse
import logging
import logging.handlers

parser = argparse.ArgumentParser(description="srv")
parser.add_argument('--path')
args = parser.parse_args()

print('a')
if __name__ == '__main__':
    # 로깅을 설정합니다. getLogger()를 통해 root를 설정해 놓으면 이후 logging으로 바로 사용해도 됩니다
    # global 영역이 아닌 main 안에 넣은 이유는 그렇게 하지 않으면 두번씩 불리면서 
    # (다른 파일 from import 할 때 그러는건지) 파일에 두번씩 기록되었기 때문입니다
    log = logging.getLogger(log_path)
    log.setLevel(logging.INFO)
    #fileHandler = logging.FileHandler('/home/pi/wowinfo.log')
    myhome = str(pathlib.Path.home())
    fileHandler = logging.handlers.RotatingFileHandler(filename=myhome+'/wowinfo.log', maxBytes=10*1024*1024,
                                                   backupCount=10)
    fileHandler.setFormatter(logging.Formatter('[%(asctime)s]-(%(name)s)-%(message)s'))
    log.addHandler(fileHandler)
    app = web.Application()
    # configure app

    args = parser.parse_args()
    #web.run_app(init(), port=7777)
    web.run_app(init(app), path=args.path, port=args.port)
