import csv,re,sys,time,threading
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin,urlparse
import tkinter as tk
from tkinter import ttk,messagebox
import requests
from bs4 import BeautifulSoup

BROKER='https://fmi.se/soktjanster/sok-maklare/'
COMPANY='https://fmi.se/soktjanster/sok-maklarforetag/'
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/153 Safari/537.36'
COUNTIES=['Blekinge','Dalarna','Gotland','Gävleborg','Halland','Jämtland','Jönköping','Kalmar','Kronoberg','Norrbotten','Skåne','Stockholm','Södermanland','Uppsala','Värmland','Västerbotten','Västernorrland','Västmanland','Västra Götaland','Örebro','Östergötland']
FIELDS=['record_type','name','company','company_member_count','street','postal_code','city','phone','email','website','fmi_url','scraped_at']
def clean(s): return re.sub(r'\s+',' ',s or '').strip()
def detail_url(href,kind):
 if not href:return None
 u=urljoin('https://fmi.se',href); p=urlparse(u)
 if p.netloc.lower() not in ('fmi.se','www.fmi.se'):return None
 expected='/soktjanster/sok-maklare/' if kind=='broker' else '/soktjanster/sok-maklarforetag/'
 if p.path.rstrip('/')+'/'!=expected:return None
 return u if re.fullmatch(r'\d+',dict([x.split('=',1) for x in p.query.split('&') if '=' in x]).get('id','')) else None
def links(html,kind):
 s=BeautifulSoup(html,'html.parser'); out=[]
 for a in s.select('a[href]'):
  u=detail_url(a.get('href'),kind)
  if u and u not in out:out.append(u)
 return out
def parse_detail(url,html,kind):
 s=BeautifulSoup(html,'html.parser'); main=s.find('main') or s
 lines=[clean(x) for x in main.get_text('\n',strip=True).splitlines() if clean(x)]
 rec={k:'' for k in FIELDS}; rec.update(record_type=kind,fmi_url=url,scraped_at=datetime.now().isoformat(timespec='seconds'))
 marker='Antal träffar:'
 try: body=lines[next(i for i,x in enumerate(lines) if x.startswith(marker))+1:]
 except StopIteration: body=lines
 for stop in ('Snabbsök','Vanliga frågor om sök'):
  try: body=body[:next(i for i,x in enumerate(body) if x.startswith(stop))]
  except StopIteration: pass
 if kind=='company':
  if body: rec['name']=body[0]
  if len(body)>1 and body[1].startswith('('): rec['company']=body[1].strip('() ')
  try:
   i=body.index('Postadress'); a=[]
   for x in body[i+1:]:
    if x in ('Kontor','Typ av registrering','Senaste registreringsdatum','Verksamma mäklare inom företaget') or x.startswith('Kopiera direktlänk'):break
    a.append(x)
   if a:
    rec['street']=a[0]
    if len(a)>1:
     m=re.search(r'^(\d{3}\s?\d{2})\s+(.+)$',a[1]); rec['postal_code']=m.group(1) if m else ''; rec['city']=m.group(2) if m else a[1]
  except ValueError:pass
  try:
   i=body.index('Verksamma mäklare inom företaget'); tail=body[i+1:]; rec['company_member_count']=str(sum(1 for x in tail if x and ',' not in x and not x.startswith('Kopiera') and not x.startswith('http') and x!='Saknar kontorsadress'))
  except ValueError:pass
 else:
  if body: rec['name']=body[0]
  try:
   i=body.index('Företag')
   rec['company']=body[i+1] if i+1<len(body) else ''
   rec['street']=body[i+2] if i+2<len(body) else ''
   if i+3<len(body):
    m=re.search(r'^(\d{3}\s?\d{2})\s+(.+)$',body[i+3]); rec['postal_code']=m.group(1) if m else ''; rec['city']=m.group(2) if m else body[i+3]
  except ValueError:pass
 return rec
def discover(kind,n,log):
 from selenium import webdriver
 from selenium.webdriver.common.by import By
 from selenium.webdriver.common.keys import Keys
 from selenium.webdriver.support.ui import WebDriverWait
 from selenium.webdriver.support import expected_conditions as EC
 from selenium.common.exceptions import ElementClickInterceptedException, StaleElementReferenceException
 base=BROKER if kind=='broker' else COMPANY
 d=webdriver.Chrome()
 d.set_page_load_timeout(40)
 found=[]
 def dismiss_overlays():
  # FMI explicitly displays a cookie/message banner with a "Stäng meddelandet" button.
  for e in d.find_elements(By.XPATH,"//*[self::button or self::a][contains(normalize-space(.),'Stäng meddelandet')]"):
   try:
    if e.is_displayed():
     d.execute_script("arguments[0].click();",e)
     time.sleep(.25)
   except Exception: pass
 def js_click(e):
  d.execute_script("arguments[0].scrollIntoView({block:'center',inline:'center'});",e)
  try:
   e.click()
  except ElementClickInterceptedException:
   d.execute_script("arguments[0].click();",e)
 def wait_results():
  time.sleep(1.5)
  # Results are direct FMI record links; never follow generic navigation links.
  for a in d.find_elements(By.CSS_SELECTOR,'a[href]'):
   u=detail_url(a.get_attribute('href'),kind)
   if u and u not in found: found.append(u)
 try:
  d.get(base)
  WebDriverWait(d,20).until(EC.presence_of_element_located((By.TAG_NAME,'body')))
  dismiss_overlays()
  for county in COUNTIES[:n]:
   log('FMI: '+county)
   dismiss_overlays()
   ins=d.find_elements(By.CSS_SELECTOR,'input[type="search"],input[name="q"],input.ant-input,input[type="text"]')
   target=None
   for e in ins:
    try:
     if e.is_displayed() and e.is_enabled():
      ph=(e.get_attribute('placeholder') or '').lower()
      name=(e.get_attribute('name') or '').lower()
      if 'fritext' in ph or 'sök' in ph or name in ('q','search','query'):
       target=e; break
    except StaleElementReferenceException: pass
   if target is None:
    target=next((e for e in ins if e.is_displayed() and e.is_enabled()),None)
   if target is None:
    raise RuntimeError('FMI-sökfältet "Fritext" hittades inte')
   d.execute_script("arguments[0].scrollIntoView({block:'center'});",target)
   try:
    target.click()
   except ElementClickInterceptedException:
    dismiss_overlays()
    d.execute_script("arguments[0].click();",target)
   target.send_keys(Keys.CONTROL,'a')
   target.send_keys(county)
   # FMI documentation says Enter in the quick-search field performs the search.
   target.send_keys(Keys.ENTER)
   wait_results()
   # If the suggestion UI swallowed Enter, explicitly invoke the visible Sök button.
   if not any(county.lower() in (d.find_element(By.TAG_NAME,'body').text or '').lower() for _ in [0]):
    buttons=d.find_elements(By.XPATH,"//button[normalize-space(.)='Sök'] | //input[@type='submit']")
    for b in buttons:
     try:
      if b.is_displayed() and b.is_enabled():
       js_click(b); wait_results(); break
     except Exception: pass
 finally:
  d.quit()
 return found

def run(broker,company,n,out,log):
 sess=requests.Session();sess.headers['User-Agent']=UA; urls=[]
 if broker:urls+=discover('broker',n,log)
 if company:urls+=discover('company',n,log)
 urls=list(dict.fromkeys(urls));log('Direkta FMI-detaljsidor: '+str(len(urls)));rows=[]
 for i,u in enumerate(urls,1):
  kind='broker' if '/sok-maklare/' in u else 'company';log(f'{i}/{len(urls)} {u}')
  r=sess.get(u,timeout=30);r.raise_for_status();rows.append(parse_detail(u,r.text,kind));time.sleep(.25)
 out.mkdir(parents=True,exist_ok=True);p=out/'maklare_fmi.csv'
 with p.open('w',encoding='utf-8-sig',newline='') as f:csv.DictWriter(f,fieldnames=FIELDS,delimiter=';').writerows(rows)
 log(f'Klar: {p} ({len(rows)} poster)');return p
class App(tk.Tk):
 def __init__(self):
  super().__init__();self.title('MäklarScraper v2');self.geometry('700x520')
  p=ttk.Frame(self,padding=18);p.pack(fill='both',expand=True)
  ttk.Label(p,text='MäklarScraper v2',font=('Segoe UI',20,'bold')).pack(anchor='w')
  ttk.Label(p,text='FMI-baserad svensk mäklar-/företagsscraper').pack(anchor='w',pady=(0,14))
  self.b=tk.BooleanVar(value=True);self.c=tk.BooleanVar(value=True);self.n=tk.IntVar(value=21)
  ttk.Checkbutton(p,text='Mäklare',variable=self.b).pack(anchor='w');ttk.Checkbutton(p,text='Mäklarföretag',variable=self.c).pack(anchor='w')
  row=ttk.Frame(p);row.pack(anchor='w',pady=10);ttk.Label(row,text='Antal län att söka:').pack(side='left');ttk.Spinbox(row,from_=1,to=21,textvariable=self.n,width=5).pack(side='left',padx=8)
  self.btn=ttk.Button(p,text='START SCRAPER',command=self.go);self.btn.pack(anchor='w',pady=7)
  self.box=tk.Text(p,height=18,width=82);self.box.pack(fill='both',expand=True)
 def log(self,s):self.after(0,lambda:(self.box.insert('end',s+'\n'),self.box.see('end')))
 def go(self):
  if not(self.b.get() or self.c.get()):return
  self.btn.config(state='disabled');out=Path(sys.executable if getattr(sys,'frozen',False) else __file__).resolve().parent/'Exports'
  def w():
   try:run(self.b.get(),self.c.get(),self.n.get(),out,self.log);self.after(0,lambda:messagebox.showinfo('Klar','Scrapningen är klar. Se Exports.'))
   except Exception as e:self.log('FEL: '+repr(e));self.after(0,lambda:messagebox.showerror('Fel',str(e)))
   finally:self.after(0,lambda:self.btn.config(state='normal'))
  threading.Thread(target=w,daemon=True).start()
if __name__=='__main__':App().mainloop()
