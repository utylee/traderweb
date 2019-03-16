import asyncio
import uvloop
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

from aiohttp import web
import datetime
import time
import argparse
import aiohttp
import logging
import logging.handlers
import aiohttp_mako 
import sqlalchemy as sa
from aiopg.sa import create_engine
#from auction import *
import auction as auc
#from auction import get_decoed_item_set, get_decoed_item, db_update_from_server
#from auction_classes import *
import auction_classes as a_cl
#from auction_classes import Set
#from db_tableinfo import *
import db_tableinfo as di 
import pathlib
import aioredis

parser = argparse.ArgumentParser(description="wowinfo")
parser.add_argument('--path')
parser.add_argument('--port')
args = parser.parse_args()
try:
    log_path = args.path[5:]
except:
    log_path = args.port

# 서버 선택
server = '아즈샤라'
serverlist = []     # 총 서버리스트는 거의 변하지 않으므로 글로벌로 최초 handle시에만 전달해줍니다
#currentset = '격아약초세트1'
currentset = '기본구성'
defaultset = '기본구성'
defaultuser = 'guest'
imageroot = 'https://wow.zamimg.com/images/wow/icons/large/'

# 관심 아이템들 목록
pin_items = ['하늘 골렘', '아쿤다의 이빨', '닻풀', # 심해 가방', '사술매듭 가방'
            '살아있는 강철', '민첩의 전투 물약', '물결의 영약'] #'호화로운 모피']
#pin_items = ['살아있는 강철', '하늘 골렘']

# fetch 실행 주기 :5분
interval = 1800 #초
interval = 3600 #초
ws = 0
ar = {} 

# 웹소켓 핸들러입니다
async def ws_handle(request):
    global ws
    ws = web.WebSocketResponse()
    #print(ws)
    await ws.prepare(request)
    #print(ws)

    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            if msg.data == 'connect':
                log.info('connected')
                #await ws.send_str('1')
                '''
                print('update on connect')
                log.info('update on connect')
                await ws.send_str('update')
                '''
            elif msg.data == 'close':
                await ws.close()
        elif msg.type == aiohttp.WSMsgType.ERROR:
            print('ws connecion closed with exception {}'.format(ws.exception()))

        ''' nginx server{}에 ws관련해서 따로 설정을 해줘야합니다
        아 그냥 /ws이 아닌 / 에 아래값을 추가해주니 되네요
        location /ws {
            proxy_pass http://aiohttp;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
        '''

    return ws

@aiohttp_mako.template('index.html')
async def user(request):
    global server
    #global currentset
    global imageroot
    global serverlist
    log.info('/user handler came in')
    user_code = request.match_info['user_code']
    currentset = ''
    currentset_code = ''
    try: 
        currentset_code = request.match_info['itemset_code']
        log.info(f'itemset_code: {currentset_code}')
    except:
        currentset_code = 'default'
        log.info(f'exeption!! itemset_code: {currentset_code}')

    redis_top5 = []
    redis = request.app['redis']
    for i in ['1','2','3','4','5']:
        val = await redis.get(i)
        redis_top5.append(val)
    
    user = await auc.get_user_from_code(request.app['db'], user_code)
    log.info(f'{user}')
    currentset = await auc.get_itemset_from_code(request.app['db'], user, currentset_code)
    log.info(f'{currentset}')
    #해당코드의 아이템셋이 없을 경우 default인 user를 줍니다
    if(not currentset):
        currentset = user
        currentset_code = 'default'
    #최적화를 위해서 굳이 db에서 가져오지 않습니다. 0.2초 단축 200ms
    #itemsets = await get_itemsets()
    itemsets = []
    # default set이냐 아니냐로 분기하기 위함입니다
    #set_ = a_cl.Set(currentset).fork()
    #dict_ = await set_.get_decoed_item_set(server)
    dict_ = {}

    log.info('last')
    return {'name': '7', 'imageroot': imageroot ,'ar':dict_, 'server':server, 'user':user, 
            'user_code':user_code, 'serverlist':serverlist, 'itemsets': itemsets,
            'current_itemset':currentset, 'current_itemset_code':currentset_code, 'top_5':redis_top5}


async def login(request):
    log.info('/login handler came in')
    user = request.match_info['user_name']
    data = {}
    start_time = time.time()
    success, code = await auc.login(request.app['db'], user)
    finished_time = time.time()
    proc_time = round(finished_time - start_time, 3)
    log.info(f'login success: {success}, code:{code} ({proc_time})초')
    data['name'] = user
    data['code'] = code
    data['success'] = success

    start_time = time.time()
    data['itemsets'] = await get_itemsets(request, user)
    finished_time = time.time()
    proc_time = round(finished_time - start_time, 3)
    log.info(data)
    log.info(f'login get_itemsets:: fetch elapsed time: {proc_time} 초')

    return web.json_response(data)

async def create_user(request):
    log.info('/create_user handler came in')
    name = request.match_info['user_name']
    data = {}
    success, code = await auc.create_user(request.app['db'], name, defaultset)
    log.info(f'success: {success}, code:{code}')
    data['name'] = name
    data['code'] = code
    data['success'] = success

    return web.json_response(data)

async def create_itemset(request):
    print('/create_itemset handler came in')
    log.info('/create_itemset handler came in')
    user = request.match_info['cur_user']
    setname = request.match_info['setname'].strip()
    success = await auc.create_itemset(request.app['db'], user, setname, defaultuser, defaultset) 
    data = {}
    data['success'] = success

    return web.json_response(data)

async def delete_itemset(request):
    print('/delete_itemset handler came in')
    log.info('/delete_itemset handler came in')
    user = request.match_info['cur_user']
    setname = request.match_info['setname']
    success = await auc.delete_itemset(request.app['db'], user, setname)
    data = {}
    data['success'] = success

    return web.json_response(data)

async def update_indiv(request):
    log.info('/update_indiv handler came in')
    pos_no = request.match_info['num']
    item_name = request.match_info['itemname']
    fullstr = request.match_info['fullstr']
    srver = request.match_info['server']
    user = request.match_info['cur_user']
    item_set = request.match_info['cur_itemset']

    l_full = fullstr.split(',')
    log.info(f'full_str:{l_full}')
    '''
    num = int(pos_no)
    item_name = l_full[num]
    l_full.pop(num)
    log.info(f'remain_str:{l_full}')
    '''
    success = 1
    a = time.time()
    indiv_ar = await auc.get_decoed_item(request.app['db'], srver, user, item_set, pos_no, item_name, fullstr)
    b = time.time()
    sub = round(b - a,2)
    print(f':{sub}초 소요')
    log.info(f':{sub}초 소요')
    if(not indiv_ar):
        success = 0
    data = {}
    data['indiv_ar'] = indiv_ar 
    data['num'] = pos_no
    data['success'] = success

    return web.json_response(data)

async def rq_itemsets(request):
    log.info('/rq_itemsets handler came in')

    user = request.match_info['cur_user']
    log.info(f'cur_user:{user}')

    data = {}
    start_time = time.time()
    data['itemsets'] = await get_itemsets(request, user)
    finished_time = time.time()
    proc_time = round(finished_time - start_time, 3)
    log.info(data)
    log.info(f'rq_itemsets:: fetch elapsed time: {proc_time} 초')

    return web.json_response(data)

async def rq_itemset(request):
    #global currentset
    log.info('/rq_itemset handler came in')

    itemset = request.match_info['itemset']
    user = request.match_info['cur_user']
    log.info(f'itemset:{itemset}')
    start_time = time.time()
    set_ = a_cl.Set(itemset).fork()
    code, dict_ = await set_.get_only_itemset(request.app['db'], user)
    finished_time = time.time()
    proc_time = round(finished_time - start_time, 3)
    log.info(f'rq_itemset:: fetch elapsed time: {proc_time} 초')

    data = {}
    data['data'] = dict_
    data['code'] = code
    log.info(data)
    return web.json_response(data)

async def rq_item(request):
    log.info('/rq_item handler came in')

    #user = request.match_info['cur_user']
    num = request.match_info['num']
    item = request.match_info['item']
    #fullstr = request.match_info['fullstr']
    srver = request.match_info['server']
    #cur_user = request.match_info['cur_user']

    #log.info(f'fullstr: {fullstr}')
    a = time.time()
    indiv_ar = await auc.get_decoed_item(request.app['db'], srver, '', '', num, item) #user 및set명은 비워서제출
    b = time.time()
    sub = round(b - a,2)
    log.info(f'rq_item:: fetch elapsed time: {sub} 초')
    data = {}
    data['itemdata'] = indiv_ar 
    data['num'] = num

    return web.json_response(data)

async def rq_servertime(request):
    #global currentset
    log.info('/rq_servertime handler came in')
    data = {}

    srver = request.match_info['server']
    start_time = time.time()
    engine = request.app['db']
    async with engine.acquire() as conn:
        async for r in conn.execute(di.tbl_wow_server_info.select().where(di.tbl_wow_server_info.c.server==srver)):
            data['time'] = r[1]
    finished_time = time.time()
    proc_time = round(finished_time - start_time, 3)
    log.info(f'fetch elapsed time: {proc_time} 초')
    data['server'] = srver
    log.info(f'data: {data}')

    return web.json_response(data)

async def update(request):
    global ar
    global server
    global serverlist
    #global currentset
    itemset = ''
    log.info('/update handler came in')

    itemset = request.match_info['itemset']
    srver = request.match_info['server']
    user = request.match_info['cur_user']
    '''
    proto = request.match_info['proto']
    print(f':itemset = {itemset}')
    if(proto == '_default'):
        print('DEFAULT!!!!')
        '''

    '''
    if currentset != itemset:
        currentset = itemset
        ar = await get_decoed_item_set(server, currentset)
    '''
    # 굳이 글로벌로 균일하게 갖고 있는 것은 말이 안됩니다. 사용자가 원하는 상황마다 그대로 전달해줘야합니다
    start_time = time.time()
    set_ = a_cl.Set(itemset).fork()
    dict_ = await set_.get_decoed_item_set(request.app['db'], srver)
    #dict_ = {}
    finished_time = time.time()
    proc_time = round(finished_time - start_time, 3)
    log.info(f'fetch elapsed time: {proc_time} 초')

    data = {}
    itemsets = []

    #conn = await request.app['db'].cursor() 
    async with request.app['db'].acquire() as conn:
        async for r in conn.execute(di.tbl_wow_server_info.select().where(di.tbl_wow_server_info.c.server==srver)):
            data['time'] = r[1]

    #data['time'] = ''
    data['ar'] = dict_
    data['itemsets'] = await get_itemsets(request, user)
    #data['itemsets'] = []

    #data['serverlist'] = await auc.get_serverlist() # get_serverlist가 처음 handle시에삽입되어 있습니다
    data['serverlist'] = serverlist 

    return web.json_response(data)

@aiohttp_mako.template('index.html')
async def handle(request):
    #return web.Response(text='fuck')
    global ar
    global server
    global currentset
    global imageroot
    global serverlist
    
    #redis로부터 top5 가져옴
    keys_top5 = ['1','2', '3', '4', '5']
    redis_top5 = []
    redis = request.app['redis']
    for i in keys_top5:
        val = await redis.get(i)
        redis_top5.append(val)
    
    #최적화를 위해서 굳이 db에서 가져오지 않습니다. 0.2초 단축 200ms
    #itemsets = await get_itemsets()
    itemsets = []
    # default set이냐 아니냐로 분기하기 위함입니다
    set_ = a_cl.Set(currentset).fork()
    #dict_ = await set_.get_decoed_item_set(server)
    dict_ = {}
    currentset_code = 'default'

    '''
    return {'name': '7', 'imageroot': '../static/images/' ,'ar':ar, 'server':server,
                    'itemsets': itemsets, 'current_itemset':currentset}
    '''
    return {'name': '7', 'imageroot': imageroot ,'ar':dict_, 'server':server, 'user':'guest','user_code':'',
                    'serverlist':serverlist, 'itemsets': itemsets, 
                    'current_itemset':currentset, 'current_itemset_code':currentset_code,
                    'top_5':redis_top5}

async def init(app):
    global interval
    global ws

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
    app.router.add_get('/u/{user_code}/{itemset_code:.*}', user)
    app.router.add_get('/u/{user_code}', user)
    app.router.add_get('/update/{server}/{cur_user}/{itemset}/{dummy}', update)
    app.router.add_get('/update/{server}/{cur_user}/{itemset}', update)
    app.router.add_get('/rq_servertime/{server}/{dummy}', rq_servertime)
    app.router.add_get('/rq_servertime/{server}', rq_servertime)
    app.router.add_get('/rq_itemset/{cur_user}/{itemset}/{dummy}', rq_itemset)
    app.router.add_get('/rq_itemsets/{cur_user}/{dummy}', rq_itemsets)
    app.router.add_get('/rq_item/{num}/{server}/{item}/{dummy}', rq_item)
    #app.router.add_get('/rq_item/{cur_user}/{num}/{server}/{fullstr}/{dummy}', rq_item)
    app.router.add_get('/update_indiv/{num}/{server}/{cur_user}/{cur_itemset}/{itemname}/{fullstr}/{dummy}',
                                update_indiv)
    #app.router.add_get('/update_indiv/{num}/{server}/{cur_user}/{cur_itemset}/{itemname}/{dummy}',
                                #update_indiv)
    app.router.add_get('/create_user/{user_name}', create_user)
    app.router.add_get('/login/{user_name}', login)
    app.router.add_get('/create_itemset/{cur_user}/{setname}', create_itemset)
    app.router.add_get('/delete_itemset/{cur_user}/{setname}', delete_itemset)

    # 웹소켓 핸들러도 get을 통해 정의해줘야합니다
    ws = app.router.add_get('/ws', ws_handle)

    # db에 바로 접속해 놓습니다
    engine = await create_engine(user='postgres',
                            database='auction_db',
                            host='localhost',
                            password='sksmsqnwk11')

    app['db'] = engine
    #별도의 db proc을 돌리므로 뺍니다. 불필요한 업데이트가 초반 두번 일어나는 결과를 불러옵니다
    '''
    loop = asyncio.get_event_loop()
    loop.create_task(main_proc(interval))
    '''
    loop = asyncio.get_event_loop()
    app['loop'] = loop
    loop.create_task(init_proc(app['db']))

    app['redis'] = await aioredis.create_redis('redis://localhost', loop=loop)

    # 서버리스트를 가져오고 (X 최초아이템 셋도 가져옵니다)
    #init_data()

    return app

async def init_proc(engine):
    global serverlist
    #log.info(f'init serverlist size: {len(serverlist)}')
    if(len(serverlist) == 0):
        serverlist = await auc.get_serverlist(engine)
        #log.info(f'after serverlist size: {len(serverlist)}')


async def main_proc(intv):
    # 현재 동작 안합니다. 별도로 분리
    # 한국 와우 서버 리스트를 가져옵니다
    serverlist = []
    async with create_engine(user='postgres',
                            database='auction_db',
                            host='192.168.0.212',
                            password='sksmsqnwk11') as engine:
        async with engine.acquire() as conn:
            async for r in conn.execute(di.tbl_wow_server_info.select()):
                serverlist.append(r[0])

    # 제거해봅니다. 초기에 굳이 하지 않아도 handle(index.html)가 처리합니다
    #await fetch_auction()
    
    serverlist = ['아즈샤라']
    # 주기마다 반복합니다
    while True:
        loop = asyncio.get_event_loop()
        loop.create_task(timer_proc(serverlist))
        await asyncio.sleep(intv)

async def timer_proc(serverlist):
    for s_ in serverlist:
        await auc.db_update_from_server(s_, defaultset)
        await fetch_auction()

async def fetch_auction():
    print('.경매장 정보 가져오기 시작')
    log.info('.경매장 정보 가져오기 시작')

    global ws
    global ar
    global currentset
    global server

    #ar = await get_decoed_item_set(server, currentset)

    print('update in fetch')
    log.info('update in fetch')
    try:
        print('ws: send update string')
        log.info('ws: send update string')
        await ws.send_str('update')
    except:
        print('ws send err!!!!')
        log.info('ws send err!!!!')

def init_data():
    #global ar
    global serverlist

    '''
    ar = {'사술매듭 가방': {'num': 10, 'min': 1379999900, 'min_seller': '밀림왕세나씨', 'min_chain':'0'}, 
                '심해 가방': {'num': 300, 'min': 18000000, 'min_seller': '인중개박살'}, 
                '호화로운 모피': {'num': 158, 'min': 4000, 'min_seller': '우렝밀렵'}, 
                '하늘 골렘': {'num': 173, 'min': 18560000, 'min_seller': '남미왕'}, 
                '살아있는 강철': {'num': 77, 'min': 34900000, 'min_seller': '임리치'}, 
                '민첩의 전투 물약': {'num': 25, 'min': 3505000, 'min_seller': 'Spit'}}
    for a in ar.keys():
        ar[a]['image'] = 'inv_tailoring_hexweavebag.jpg'
        min_chain = []
        for c_ in range(0, 1440):
            min_chain.append(0)
        ar[a]['min_chain'] = min_chain 
        ar[a]['gold'] = 0
        ar[a]['silver'] =0
        ar[a]['copper'] =0
        '''

async def get_itemsets(request, user):
    itemset_names = []
    async with request.app['db'].acquire() as conn:
        async for r in conn.execute(di.tbl_item_set.select().where(di.tbl_item_set.c.user==user)):
            itemset_names.append(r[0])
    return sorted(itemset_names)

#web.run_app(init(),port=7777)
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
