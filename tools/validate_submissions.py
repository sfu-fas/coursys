#!/usr/bin/env python

extracted="/tmp/120"
archive="/home/ggbaker/co/sub/submitted_files"

course="1107-cmpt-120-d500"
assign="a2"

import os, os.path

def rm_svn(dirlist):
    try:
        dirlist.remove(".svn")
    except ValueError:
        pass

def get_filename(directory):
    """
    Get the filename of the submitted file in this directory
    """
    files = os.listdir(arch_file)
    rm_svn(files)
    assert(len(files)==1)
    return files[0]

submitdir = os.path.join(archive, course, assign)
users = os.listdir(submitdir)
rm_svn(users)
# look at each user's submissions
for userid in users:
    userdir = os.path.join(submitdir, userid)
    subs = os.listdir(userdir)
    subs.sort()
    subs.reverse()
    rm_svn(subs)

    # go through submissions in reverse-chronological order; make sure those submissions are the ones found
    print(userid)
    found_parts = set()
    for sub in subs:
        print(" ", sub)
        subdir = os.path.join(userdir, sub)
        parts = os.listdir(subdir)
        rm_svn(parts)
        for p in parts:
            if p not in found_parts:
                print("   ", p)
                # most current submission of this component: make sure it matches.
                found_parts.add(p)
                arch_file = os.path.join(archive, course, assign, userid, sub, p)
                fn = get_filename(arch_file)
                arch_file = os.path.join(arch_file, fn)
                                
                extr_file = os.path.join(extracted, userid, p+"_"+fn)

                arch_file_data = file(arch_file).read()
                extr_file_data = file(extr_file).read()
                assert(arch_file_data==extr_file_data)

