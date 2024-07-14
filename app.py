import os
import sys
import click
import time

from flask import Flask, url_for, render_template, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap
from flask_socketio import SocketIO
from markupsafe import escape

WIN = sys.platform.startswith('win')
if WIN:
    prefix = 'sqlite:///'
else:
    prefix = 'sqlite:////'

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = prefix + os.path.join(app.root_path, 'data.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
socketio = SocketIO(app)
bootstrap = Bootstrap(app)

start_time = time.time()
paused = True
pause_time = 0
video_source = "http://v16m-default.akamaized.net/6a26c61e1b481e4b5f033695a7551953/66945386/video/tos/alisg/tos-alisg-v-0000/o0yeA8PkroGA5Lf47g2CbQgzIWzZeuGuAHDANQ/?a=2011&bti=MzhALjBg&ch=0&cr=0&dr=0&net=5&cd=0%7C0%7C0%7C0&br=1434&bt=717&cs=0&ds=3&ft=XE5bCqT0mmjPD12uwAX73wU7C1JcMeF~O5&mime_type=video_mp4&qs=0&rc=ZTY0Nzk4N2U5ZTs3Z2c3ZEBpM3NoNGQ6ZjdxZzMzODYzNEBhMjNgNmMyNmAxNS81MWBeYSNkc3FtcjQwYnBgLS1kMC1zcw%3D%3D&vvpl=1&l=20240714161436CF15A61C1C6E6FDC300C&btag=e000a8000"

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20))


class Movie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(60))
    year = db.Column(db.String(4))


@app.cli.command()
def forge():
    """Generate fake data."""
    db.create_all()

    name = 'Grey Li'
    movies = [
        {'title': 'My Neighbor Totoro', 'year': '1988'},
        {'title': 'Dead Poets Society', 'year': '1989'},
        {'title': 'A Perfect World', 'year': '1993'},
        {'title': 'Leon', 'year': '1994'},
        {'title': 'Mahjong', 'year': '1996'},
        {'title': 'Swallowtail Butterfly', 'year': '1996'},
        {'title': 'King of Comedy', 'year': '1999'},
        {'title': 'Devils on the Doorstep', 'year': '1999'},
        {'title': 'WALL-E', 'year': '2008'},
        {'title': 'The Pork of Music', 'year': '2012'},
    ]

    user = User(name=name)
    db.session.add(user)
    for m in movies:
        movie = Movie(title=m['title'], year=m['year'])
        db.session.add(movie)
    
    db.session.commit()
    click.echo('Done.')


@app.route('/')
def hello():
    return render_template('index.html')


@app.route('/get_video_source')
def get_video_source():
    print("get_video")
    return jsonify({'video_source': video_source})


@app.route('/control_panel')
def control_panel():
    return render_template('control_panel.html')


@app.route('/api/control', methods=['POST'])
def control_callback():
    global start_time, paused, pause_time, video_source
    action = request.json.get('action')
    value = request.json.get('value')

    match action:
        case 'seek':
            new_time = float(value)
            if paused:
                pause_time = new_time
            else:
                start_time = time.time() - new_time
            socketio.emit('seek', {'time': new_time, 'paused': paused})
        case 'play':
            if paused:
                start_time = time.time() - pause_time
                paused = False
            socketio.emit('play')
        case 'pause':
            if not paused:
                pause_time = time.time() - start_time
                paused = True
            socketio.emit('pause')
        case 'changeVideoSource':
            video_source = value
            pause_time = 0
            paused = True
            socketio.emit('changeVideoSource', {'video_source': video_source})
        
    return jsonify({'success': True})



@app.route('/user/<name>')
def user_page(name):
    return f'User: {escape(name)}'


@app.route('/test')
def test_url_for():
    # 下面是一些调用示例（请访问 http://localhost:5000/test 后在命令行窗口查看输出的 URL）：
    print(url_for('hello'))  # 生成 hello 视图函数对应的 URL，将会输出：/
    # 注意下面两个调用是如何生成包含 URL 变量的 URL 的
    print(url_for('user_page', name='greyli'))  # 输出：/user/greyli
    print(url_for('user_page', name='peter'))  # 输出：/user/peter
    print(url_for('test_url_for'))  # 输出：/test
    # 下面这个调用传入了多余的关键字参数，它们会被作为查询字符串附加到 URL 后面。
    print(url_for('test_url_for', num=2))  # 输出：/test?num=2
    return 'Test page'


@socketio.on('connect')
def handle_connect():
    print('Client connected')


@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')


@socketio.on('synchronize')
def handle_synchornize():
    global paused, pause_time
    current_time = pause_time if paused else (time.time() - start_time)
    socketio.emit('current_time', {'time': current_time, 'paused': paused})

