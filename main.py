import requests
import json
import base64
import pickle
import random
import os

from auth import user_auth

def get_blob(url):
    r = requests.get(url, auth = user_auth)
    if r.ok:
        blob_json = json.loads(r.text)
        return base64.b64decode(blob_json['content'])

def sample_repo_nr(nr):
    r = requests.get('https://api.github.com/repositories?since=' + str(nr), auth = user_auth)
    if (r.ok):
        repoList = json.loads(r.text)
        repo_url = repoList[0]['url']
        ref_url = repo_url + '/git/refs/heads/master'
        r = requests.get(ref_url, auth = user_auth)
        if r.ok:
            ref = json.loads(r.text)
            repo_tree_url = repo_url + '/git/trees/' + ref['object']['sha'] + '?recursive=1'
            r = requests.get(repo_tree_url, auth = user_auth)
            if r.ok:
                repo_tree = json.loads(r.text)
                actual_tree = repo_tree['tree']
                non_folders = [x for x in actual_tree if x['type'] == 'blob']
                blobs = []
                try:
                    # Pick 5 random files to download
                    for x in random.sample(non_folders, 5):
                        blobs.append((x, get_blob(x['url'])))
                    return blobs
                except ValueError:
                    # not 5 files, consider repository failed
                    pass
            else:
                print [r.status_code, repo_tree_url]
    print "failed"
    return []

def save_repo_nr(nr, folder):
    repo_contents = sample_repo_nr(nr)
    f = open(folder + '/' + str(nr), 'w')
    pickle.dump(repo_contents, f)
    f.close()

def roll_up(folder):
    alldata_file_name = folder + '/all_data'

    all_files = [x for x in os.listdir(folder) if x.isdigit()]
    try:
        # load previously saved data
        data = pickle.load(open(alldata_file_name))
    except:
        # no previously saved data, start fresh
        data = []
    for fname in all_files:
        f = open(folder + '/' + fname,'r')
        data.extend(pickle.load(f))

    alldata_file = open(alldata_file_name, 'w')
    pickle.dump(data, alldata_file)

    # remove all the rolled up data files
    for d in all_files:
        os.remove(folder + '/' + d)



if __name__=="__main__":
    for i in range(10):
        save_repo_nr(random.randint(1,2000000), 'data')
    roll_up('data')
