import requests
import json
import base64
import pickle
import random
import os
import re
import string
import argparse
import collections
import itertools

from pygments.lexers import guess_lexer_for_filename


from auth import user_auth

HISTORY_SIZE = 20

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


def language(blob):
    try:
        return guess_lexer_for_filename(blob[0]['path'],blob[1]).name
    except Exception:
        return 'Unknown'

def language_count_from_folder(folder):
    alldata_file_name = folder + '/all_data'
    data = pickle.load(open(alldata_file_name))
    langs = [language(x) for x in data]
    c = collections.Counter(langs)
    return dict(c)

def get_structure(lang_str):
    new_str = re.sub(r'\t','    ',re.sub(r'\S','X',lang_str))
    newline_str = string.split(new_str,"\n")
    lines = [map(len, string.split(x," ")) + [-1] for x in newline_str]
    return list(itertools.chain.from_iterable(lines)) + [-2]

def all_structures_from_folder(folder):
    alldata_file_name = folder + '/all_data'
    data = pickle.load(open(alldata_file_name))
    structures = [get_structure(x[1]) for x in data]
    return structures

def lang_structures_from_folder(folder, lang):
    alldata_file_name = folder + '/all_data'
    data = pickle.load(open(alldata_file_name))
    structures = [get_structure(x[1]) for x in data if language(x) == lang]
    return structures

def collect_stats(structures):
    likelihoods = {}
    for struct in structures:
        for start in range(0, len(struct) + 1):
            try:
                likelihoods[tuple(struct[max(0, start - HISTORY_SIZE):start])] += 1
            except KeyError:
                likelihoods[tuple(struct[max(0, start - HISTORY_SIZE):start])] = 1
    del likelihoods[()]
    return likelihoods

def sample(stats, keys):
    rand_max = sum([stats[x] for x in keys])
    if rand_max == 0:
        # no keys valid, assume global likelihood
        return -2
    offset = random.randint(1, rand_max)
    total = 0
    idx = -1
    while total < offset:
        idx += 1
        total += stats[keys[idx]]
    return keys[idx][-1]


def generate_next(stats, history):
    if history != []:
        keys = [x for x in stats.keys() if x[-(len(history) + 1):-1] == tuple(history)]
    else:
        keys = [x for x in stats.keys() if len(x) == 1]
    res = [sample(stats, keys)]
    return res
    
def generate_file_for_language(folder, lang):
    structures = lang_structures_from_folder(folder, lang)
    if len(structures) == 0:
        raise Exception("Found no data for language " + lang)
    stats = collect_stats(structures)
    res = []
    while res == [] or res[-1] != -2:
        res = res + generate_next(stats, res[-2:])
        print len(res)
    resstr = ""
    for token in res[:-1]:
        if token == 0:
            resstr += " "
        elif token == -1:
            resstr += "\n"
        else:
            resstr += " " + ('X' * token)
    return resstr

if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", help="fetchdata or generate")
    parser.add_argument("opt", help="nr or language")
    args = parser.parse_args()

    if args.action == "fetchdata":
        for i in range(int(args.opt)):
            save_repo_nr(random.randint(1,2000000), 'data')
        roll_up('data')
    elif args.action == "generate":
        print generate_file_for_language('data', args.opt)
    elif args.action == "langcount":
        print language_count_from_folder('data')