import requests

url = "https://apicatalog.mziq.com/filemanager/company/50c1bd3e-8ac6-42d9-884f-b9d69f690602/filter/categories/year/meta"

r = requests.get(url)

print(r.status_code)
print(r.json())