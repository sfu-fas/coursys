#!/usr/bin/env python

# based on http://www.davidgrant.ca/limit_size_of_subversion_commits_with_this_hook
# (but mostly rewritten to do a different job)

# hooks/pre-commit should be:
#   #!/bin/sh
#   REPOS="$1"
#   TXN="$2"
#   QUOTA="1000000000"
#   /path/to/this/check_quota.py "$REPOS" "$TXN" "$QUOTA" || exit 1

import sys, os, subprocess
ADMIN_EMAIL = "helpdesk@cs.sfu.ca"

# http://stackoverflow.com/questions/1392413/calculating-a-directory-size-using-python
# (unused on the theory that du -sb is faster.)
def getFolderSize(folder):
    total_size = os.path.getsize(folder)
    for item in os.listdir(folder):
        itempath = os.path.join(folder, item)
        if os.path.isfile(itempath):
            total_size += os.path.getsize(itempath)
        elif os.path.isdir(itempath):
            total_size += getFolderSize(itempath)
    return total_size
 
def printUsage():
  sys.stderr.write('Usage: %s "$REPOS" "$TXN" "$QUOTA" ' % sys.argv[0])

def getRepoSize(repos):
  """
  Return size of repo database (in bytes).
  """
  # db directory contains the current transaction data at this point, so we're implicitly counting it.
  repo_data = os.path.join(repos, "db")
  #repo_size = getFolderSize(repo_data) # du should be faster?
  du = subprocess.check_output(['du', '-sb', repo_data])
  repo_size = int(du.split()[0])

  return repo_size

def checkRepoSize(repos, quota):
  size = getRepoSize(repos)
  percent = 100.0*size/quota
  if size > quota:
      # fail if over
      sys.stderr.write("Repository is over its disk quota: cannot commit. Contact %s for help.\n" % (ADMIN_EMAIL))
      sys.stderr.write("Quota is %i bytes; with this commit, you're using %i bytes.\n" % (quota, size))
      sys.exit(1)
  #elif 2*size > quota:
  #    # would be nice to warn if >50%
  #    sys.stderr.write("Quota is %i bytes; with this commit, you're using %i bytes.\n" % (quota, size))
 
if __name__ == "__main__":
  #Check that we got a repos, transaction, and quota with this script
  if len(sys.argv) != 4:
    printUsage()
    sys.exit(2)
  else:
    repos = sys.argv[1]
    txn = sys.argv[2]
    quota = int(sys.argv[3])

  checkRepoSize(repos, quota)

