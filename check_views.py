import os, subprocess, time, json, urllib.request, asyncio, base64, io
from PIL import Image
import websockets

async def check_view(view_name, view_import):
    code = f'''import flet as ft
from mobile.styles import COLORS
import database.connection as db_conn
{view_import}

async def main(page: ft.Page):
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = '#121212'
    view = {view_name}(page)
    page.views.append(view)
    page.update()

if __name__ == '__main__':
    ft.run(main)
'''
    with open('test_view_run.py', 'w', encoding='utf-8') as f:
        f.write(code)

    env = dict(os.environ)
    env['FLET_FORCE_WEB_SERVER'] = 'true'
    env['FLET_SERVER_PORT'] = '8590'

    p = subprocess.Popen(['python', 'test_view_run.py'], env=env)
    time.sleep(2)

    edge = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
    cmd = [edge, '--headless', '--remote-debugging-port=9250', 'http://127.0.0.1:8590/']
    p_edge = subprocess.Popen(cmd)
    time.sleep(3)

    tabs = json.loads(urllib.request.urlopen('http://127.0.0.1:9250/json').read())
    target = next(t for t in tabs if '8590' in t.get('url', ''))
    ws_url = target['webSocketDebuggerUrl']

    async with websockets.connect(ws_url) as ws:
        js = '(() => { const c = (document.querySelector("flt-glass-pane").shadowRoot || document).querySelector("canvas"); return c ? c.toDataURL() : "no canvas"; })()'
        msg = {'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js}}
        await ws.send(json.dumps(msg))
        res = await ws.recv()
        data = json.loads(res)
        url = data['result']['result']['value']
        b64 = url.split(',')[1]
        im = Image.open(io.BytesIO(base64.b64decode(b64)))
        colors = im.getcolors(maxcolors=2000)
        is_gray = any(c[1] == (182, 182, 182, 255) for c in (colors or []))
        total_c = len(colors) if colors else ">2000"
        print(f'{view_name}: is_gray={is_gray}, unique_colors={total_c}')

    p_edge.terminate()
    p.terminate()
    time.sleep(1)

async def run_all():
    await check_view('get_transactions_view', 'from mobile.views.transactions import get_transactions_view')
    await check_view('get_budgets_view', 'from mobile.views.budgets import get_budgets_view')
    await check_view('get_investments_view', 'from mobile.views.investments import get_investments_view')

if __name__ == '__main__':
    asyncio.run(run_all())
