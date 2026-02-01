
import os
import json


def _detect(root):

    def loop_(folder, rc):
        for root, dirs, files in os.walk(folder):
            for filename in files:
                if filename.endswith('.json'):
                    rc.append(os.path.join(root, filename))
            for dirname in dirs:
                loop_(os.path.join(root, dirname), rc)
        
    filenames = []
    loop_(root, filenames)

    def is_json(data):
        try:
            json.loads(data)
        except:
            return False
        return True
    
    filenames = list(set(filenames))

    rc = []
    for filename in filenames:
        valid = False
        with open(filename, "r") as f:
            valid = is_json(f.read())
        if not valid:
            rc.append(filename)

    print(f'    {len(rc)} damaged file(s)')

    return rc


def _cleanup(folder, filenames):

    for filename in filenames:
        print(f'    remove {filename}')
        os.remove(filename)


def _main():

    user = 'Aramco'
    root = f'C:/Users/{user}/.node-red/'

    for c in ['t','d1','d2','d3','d4']:
        folder = os.path.join(root, c, 'context')
        if os.path.exists(folder):
            print(f'--- checking folder {folder}')
            rc = _detect(folder)            
            if len(rc) >0:
                _cleanup(folder, rc)

if __name__ == '__main__':
    _main()  