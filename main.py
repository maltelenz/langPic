import requests
import json
import base64

def get_blob(url):
    r = requests.get(url)
    if r.ok:
        blob_json = json.loads(r.text)
        return base64.b64decode(blob_json['content'])

def get_repo_nr(nr):
    r = requests.get('https://api.github.com/repositories?since=' + str(nr))
    if (r.ok):
        repoList = json.loads(r.text)
        repo_url = repoList[0]['url']
        ref_url = repo_url + '/git/refs/heads/master'
        r = requests.get(ref_url)
        if r.ok:
            ref = json.loads(r.text)
            repo_tree_url = repo_url + '/git/trees/' + ref['object']['sha'] + '?recursive=1'
            r = requests.get(repo_tree_url)
            if r.ok:
                repo_tree = json.loads(r.text)
                actual_tree = repo_tree['tree']
                non_folders = [x for x in actual_tree if x['type'] == 'blob']
                blobs = [get_blob(x['url']) for x in non_folders]
                return blobs
            else:
                print [r.status_code, repo_tree_url]
    print "failed"
    return []

if __name__=="__main__":
    print get_repo_nr(50003)
