import asyncio
#import uvloop
#asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

import pathlib
import argparse
import logging
import logging.handlers

from aiohttp import web
import aiohttp_mako 
import aioredis

parser = argparse.ArgumentParser(description="srv")
parser.add_argument('--path')
args = parser.parse_args()


@aiohttp_mako.template('index.html')
async def handle(request):

    return

async def init(app):

    #app = web.Application()
    # 한글 주석들이 파싱하다가 에러가 나버리는 바람에 샘플대로 encoding 옵션을 다시 모두 넣어줬습니다
    # directories 부분을 지정해주면 샘플과 달리 파일을 직접 언급해서 가져올수 있습니다
    lookup = aiohttp_mako.setup(app,directories=['html'], 
                                    input_encoding='utf-8',
                                    output_encoding='utf-8',
                                    default_filters=['decode.utf8'])
    
    #lookup = aiohttp_mako.setup(app, directories=['.'])
    #lookup.put_string('index.html', '''<h2>${name}</h2>''')

    #app.router.add_static('/static', 'static')
    app.router.add_get('/', handle)
    # 웹소켓 핸들러도 get을 통해 정의해줘야합니다
    #ws = app.router.add_get('/ws', ws_handle)

    loop = asyncio.get_event_loop()
    #app['redis'] = await aioredis.create_redis('redis://localhost', loop=loop)

    return app

if __name__ == '__main__':
    log = logging.getLogger()
    log.setLevel(logging.INFO)
    curpath = str(pathlib.Path('.'))
    fileHandler = logging.handlers.RotatingFileHandler(filename=curpath+'/traderweb.log',
                    maxBytes=10*1024*1024, backupCount=10)
    fileHandler.setFormatter(logging.Formatter('[%(asctime)s]-(%(name)s)-%(message)s'))
    log.addHandler(fileHandler)
    app = web.Application()
    web.run_app(init(app), port=7777)
