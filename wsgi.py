import sys

sys.path.append('.')

from main.app import create_app

app = create_app(name='app')

if __name__ == '__main__':
    # cobra-55555 -20-04-13
    app.run(host='0.0.0.0', port=5000)
    # // // // // //
