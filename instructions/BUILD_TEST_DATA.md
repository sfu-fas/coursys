# Building Fresh Test/Dev Data

Start with a fresh development system: empty `localsettings.py` and:

```shell
rm fixtures/*.json
rm db.sqlite
./manage.py migrate
cp db.sqlite db.empty
cp db.empty db.sqlite && ./manage.py create_test_data
git add fixtures/
```