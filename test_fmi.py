import re,requests
from maklar_scraper import parse_detail
CASES=[('https://fmi.se/soktjanster/sok-maklarforetag/?id=39398','company'),('https://fmi.se/soktjanster/sok-maklare/?id=39723','broker')]
for u,k in CASES:
 r=requests.get(u,headers={'User-Agent':'Mozilla/5.0'},timeout=30);r.raise_for_status()
 x=parse_detail(u,r.text,k)
 assert re.fullmatch(r'https://fmi\.se/soktjanster/sok-(maklare|maklarforetag)/\?id=\d+',x['fmi_url'])
 assert x['name'],(u,x)
 assert x['record_type']==k
print('FMI direct-record tests passed')
