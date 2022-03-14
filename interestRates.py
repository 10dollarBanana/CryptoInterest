################################################################################
# Import
################################################################################
from urllib.request import Request, urlopen
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.keys import Keys

import pandas as pd
import numpy as np
import json
from bs4 import BeautifulSoup
import datetime
import codecs
from requests.auth import AuthBase
import hmac
import hashlib
import requests
import time
import lxml
from APIs import *
import html5lib


################################################################################
# 1. Get Coin lists
################################################################################
server = "https://api.coingecko.com/api/v3/"

ext = "/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=300&page="

# Top 500
pList = [1,2,3]
coins = pd.DataFrame()
for i in pList:
    temp = requests.get(server+ext+str(i)).json()
    temp = pd.DataFrame(temp)
    coins = coins.append(temp)

coins['symbol'] = coins['symbol'].str.upper()

coins[coins['symbol'].str.contains('PAXG')]

gecko = coins[["symbol", "name"]]

gecko = coins[["name", "symbol"]]
gecko.columns = ["Coin", "Symbol"]

extra = pd.DataFrame(
    {'Coin': ['TrueHKD', 'TrueAUD', 'TrueCAD', 'TrueGBP', 'eToro Euro', 'eToro GBP', 'Zytara USD'],
     'Symbol': ['THKD', 'TAUD', 'TCAD', 'TGBP', 'EURX', 'GBPX', 'ZUSD']
    })

gecko = pd.merge(gecko,extra,on=["Coin", "Symbol"],how='outer')

################################################################################
# 2. Binance.us
################################################################################
print("Binance")
url = "https://www.binance.us/en/staking/products/"

QTUM="a7c34ea35b664932bdc3694266d1ddb6"
EOS="93a6e3211a194d39b845b2a87f7564de"
ONE="d7fc90d91818413d92260a06e14191b2"
VET="e5949d1808ea489881342fece7760912"
XTZ="778628a5ce534ac285f6d1ac71719ed9"
ATOM="f97540f0f5eb4a43b15033f16cb37ffe"
ALGO="b337c788f113494cae02e2798756528d"

coinList = [QTUM, EOS, ONE, VET, XTZ, ATOM, ALGO]

temp = pd.DataFrame(["Symbol", "Binance.US"]).T
temp.columns=["Symbol", "Binance.US"]

for i in coinList:  
    options = Options()
    options.headless = True
    coin=url+i
    # Load Firefox, site, wait to load
    driver = webdriver.Firefox(options=options)
    driver.get(coin)
    driver.find_element_by_xpath("/html/body/div/div/main/div/div[2]/div[3]/div/div/div[1]/div[1]/div[2]").click()
    # Grab data
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    tables = soup.find_all('table')
    new = pd.read_html(str(tables))
    driver.close()
    # Reformat data
    new = pd.DataFrame(np.concatenate(new), columns=["Date", "Distribution", "Symbol", "Binance.US"])
    new = new[["Symbol", "Binance.US"]]
    colName="Symbol"
    new[colName] = new[colName].str.split('\s').str[-1]
    new = new.iloc[0,]
    new= pd.DataFrame(new).T
    temp = pd.merge(temp,new,on=["Symbol", "Binance.US"],how='outer')

binance = temp.iloc[1:]

pd.DataFrame(tables)

# Fix values
colName = "Binance.US"
binance[colName] = binance[colName].str.replace(' %', '%')

################################################################################
# 3. Blockfi
################################################################################
print("BlockFi")
url = 'https://blockfi.com/rates/'
req = Request(url , headers={'User-Agent': 'Mozilla/5.0'})

webpage = urlopen(req).read()
page_soup = BeautifulSoup(webpage, "html.parser")
tables = page_soup.findAll("table")
blockfi = pd.read_html(str(tables))[0]

colName="Currency"
blockfi = blockfi[blockfi[colName].str.contains('Tier 1')]
blockfi[colName] = blockfi[colName].str.split('\s').str[0]

colName="APY"
blockfi[colName] = blockfi[colName].str.split('*').str[0]

blockfi.columns=["Symbol", "Drop", "BlockFi"]
blockfi = blockfi[["Symbol", "BlockFi"]]

################################################################################
# 4. Celsius
################################################################################
url = "https://celsius.network/earn-rewards-on-your-crypto"

options = Options()
options.headless = True
# Load Firefox, site, wait to load
driver = webdriver.Firefox(options=options)
driver.get(url)
time.sleep(5)

# Grab data
soup = BeautifulSoup(driver.page_source, 'html.parser')
tables = soup.find_all('table')
celsius = pd.read_html(str(tables))

# Close Firefox
driver.close()

# Reformat data
celsius = pd.DataFrame(np.concatenate(celsius), columns=["Drop", "Symbol", "Celsius"])
celsius = celsius[["Symbol", "Celsius"]]

# Fix values
colName = "Symbol"
celsius[colName] = celsius[colName].str.replace('Bitcoin', 'BTC')
celsius[colName] = celsius[colName].str.replace('Ethereum', 'ETH')
celsius[colName] = celsius[colName].str.replace('MCDAI', 'DAI')
celsius[colName] = celsius[colName].str.split('\sERC20').str[0]
celsius = celsius[celsius[colName].str.contains("After")==False]
celsius[colName] = celsius[colName].str.split('\s').str[0]

colName = "Celsius"
celsius = celsius[celsius[colName].str.contains('%')]

################################################################################
# 5. Coinbase
################################################################################
print("Coinbase")
class CoinbaseWalletAuth(AuthBase):
    def __init__(self, api_key, secret_key):
        self.api_key = coinbase_api_key
        self.secret_key = coinbase_api_secret
    def __call__(self, request):
        timestamp = str(int(time.time()))
        message = timestamp + request.method + request.path_url + (request.body or '')
        signature = hmac.new(codecs.encode(self.secret_key), msg=codecs.encode(message), digestmod=hashlib.sha256).hexdigest()
        request.headers.update({
            'CB-ACCESS-SIGN': signature,
            'CB-ACCESS-TIMESTAMP': timestamp,
            'CB-ACCESS-KEY': self.api_key,
        })
        return request

api_url = 'https://api.coinbase.com/v2/'
auth = CoinbaseWalletAuth(coinbase_api_key, coinbase_api_secret)

# Get coinlist
pagination  = {
    'limit': 100
}
accounts = requests.get(api_url + 'accounts', auth=auth, params = pagination)      
accounts = accounts.json()

coinLen = len(accounts['data'])

tkn = []
apy = []
for i in range(coinLen):
    tkn.append(accounts['data'][i]['currency'])
    try: 
        temp = str(accounts['data'][i]['rewards']['formatted_apy'])
    except KeyError:
        temp = 'NaN'
    apy.append(temp)

coinbase = pd.DataFrame(
    {'Symbol': tkn,
     'Coinbase': apy
    })

coinbase = coinbase.loc[coinbase['Coinbase'] != 'NaN']

# Fix values
colName = "Symbol"
coinbase = coinbase[~coinbase.Symbol.str.contains('ETH2')]

################################################################################
# 6. Crypto.com
################################################################################
print("CDC")
url = "https://crypto.com/us/earn"

# Load Firefox, site, wait to load
options = Options()
options.headless = True
driver = webdriver.Firefox(options=options)
driver.get(url)
time.sleep(10)
# USA
driver.find_element_by_xpath("/html/body/div[1]/div[1]/nav/div/div/div/div[3]/div/div/div[3]/div[1]/button/div/div[2]/p").click()
time.sleep(5)
#driver.find_element_by_xpath("/html/body/div[1]/div[1]/main/div/div[1]/section[1]/div/div[2]/div/button/div[1]").click()
#time.sleep(5)
driver.execute_script("window.scrollTo(0, 3000)")
time.sleep(5)
# Flexible
driver.find_element_by_xpath("/html/body/div[1]/div[1]/main/div/div[1]/section[4]/div/div[1]/div/div[1]/div/div/div/button[1]/h5").click()
time.sleep(5)
# $400 or less
driver.find_element_by_xpath("/html/body/div[1]/div[1]/main/div/div[1]/section[4]/div/div[1]/div/div[2]/div/div/div/button[1]/h5").click()
time.sleep(5)

# Grab data
soup = BeautifulSoup(driver.page_source, 'html.parser')
#apy = soup.find_all("div", attrs={'class' : 'css-11wktx'})
coin = soup.find_all("p", attrs={'class' : 'css-155zidx'})
pct = soup.find_all("p", attrs={'class' : 'css-tjk0th'})
driver.close()

# Put in table
tkn = []
for tag in coin:
    tkn.append(tag.text.strip())

apy = soup.find_all("p", attrs={'class' : 'css-462t3o'})
apy = [apy[0].text.strip()]
for tag in pct:
    apy.append(tag.text.strip())

cdc = pd.DataFrame(
    {'Coin': tkn,
     'Crypto.com': apy
    })


# Fix names
cdc["Coin"] = cdc["Coin"].str.replace('Kyber Network', 'Kyber Network Crystal')
cdc["Coin"] = cdc["Coin"].str.replace('Bancor', 'Bancor Network Token')
cdc['coin_lower'] = cdc['Coin'].str.lower()
cdc = cdc[['coin_lower', 'Crypto.com']]

# Get symbol
temp = gecko.copy()
temp['coin_lower'] = gecko['Coin'].str.lower()
temp = pd.merge(cdc,temp,on=["coin_lower"],how='left')

# Finalize
cdc = temp[['Symbol', 'Crypto.com']]

################################################################################
# 7. Gemini
################################################################################
print("Gemini")
url = 'https://www.gemini.com/earn'
req = Request(url , headers={'User-Agent': 'Mozilla/5.0'})

webpage = urlopen(req).read()
page_soup = BeautifulSoup(webpage, "html.parser")

res = page_soup.find(id= "__NEXT_DATA__")
json_object = json.loads(res.contents[0])

gemini = json_object['props']['pageProps']
#gemini = gemini['pageProps']

temp = pd.DataFrame(["Symbol", "Gemini"]).T
temp.columns=["Symbol", "Gemini"]

for rates in gemini['interestRates']:
    new = '{} {}%'.format(rates['symbol'], round(rates['apy']*100, 2)).split()
    new = pd.DataFrame(new).T
    new.columns=["Symbol", "Gemini"]
    temp = pd.merge(temp,new,on=["Symbol", "Gemini"],how='outer')

gemini = temp.iloc[1:]


################################################################################
# 8. Ledn
################################################################################
print("Ledn")
url ='https://ledn.io/legal/en/rates-terms'

# Load Firefox, site, wait to load
options = Options()
options.headless = False
driver = webdriver.Firefox(options=options)
driver.get(url)
time.sleep(5)

# Grab data
soup = BeautifulSoup(driver.page_source, 'html.parser')
tables = soup.find_all('table')
ledn = pd.read_html(str(tables))[0]

# Close Firefox
driver.close()

# Fix dataframe
ledn = pd.DataFrame(ledn)
#ledn = ledn[1:] # Remove first row
ledn.columns = ["Symbol", "Drop", "Ledn"]
ledn = ledn[['Symbol', 'Ledn']]

# Filter and fix names
colName = 'Symbol'
ledn = ledn[~ledn[colName].str.contains('Tier 2')]
ledn[colName] = ledn[colName].str.split(' ').str[0]

################################################################################
# 9. Nexo
################################################################################
print("Nexo")
url = 'https://nexo.io/earn-crypto-re?v=1'
req = Request(url , headers={'User-Agent': 'Mozilla/5.0'})

webpage = urlopen(req).read()
page_soup = BeautifulSoup(webpage, "html.parser")
nexo = page_soup.find("div", {"class":'grid grid-cols-2 sm:grid-cols-12 row-gap-16 sm:row-gap-0 lg:col-gap-32 mt-32 sm:mt-16 -mx-12 sm:mx-0'})

rates = nexo.find_all("span", attrs={'class' : 'value'})
token = nexo.find_all("small", attrs={'class' : 'block text-12 leading-120 font-medium text-gray-400'})

tkn = []
apy = []
for i in range(len(rates)):  
    # Get Token
    temp = token[i].text   
    temp = temp.splitlines()
    temp = ''.join(list(filter(lambda k: 'Interest' in k, temp)))
    tkn.append(temp.split(' Interest')[0])
    # Get APY
    temp = rates[i].text
    temp = int(temp)-4
    if temp >= 0:
        apy.append(str(temp)+"%")
    else:
        apy.append(str("0%"))

nexo = pd.DataFrame(
    {'Symbol': tkn,
     'Nexo': apy
    })



################################################################################
# 10. Voyager
################################################################################
print("Voyager")
#currentMonth = datetime.datetime.now()
#currentMonth = currentMonth.strftime("%B")
#url = "https://www.investvoyager.com/blog/voyagers-"+currentMonth.lower()+"-interest-apr-rates/"
url = 'https://rewards.investvoyager.com/interest/'
req = Request(url , headers={'User-Agent': 'Mozilla/5.0'})

webpage = urlopen(req).read()
page_soup = BeautifulSoup(webpage, "html.parser")
tables = page_soup.findAll("table")
voyager = pd.read_html(str(tables))[0]

voyager.columns=["Drop", "Voyager", "Symbol"]

colName="Symbol"
voyager[colName] = voyager[colName].str.split('\s').str[-1]

voyager=voyager[["Symbol", "Voyager"]]

################################################################################
# 11. Merge
################################################################################
print("Merge")
interest = pd.merge(gemini,gecko,on=["Symbol"],how='outer')
interest = pd.merge(celsius,interest,on=["Symbol"],how='outer')
interest = pd.merge(blockfi,interest,on=["Symbol"],how='outer')
interest = pd.merge(voyager,interest,on=["Symbol"],how='outer')
interest = pd.merge(nexo,interest,on=["Symbol"],how='outer')
interest = pd.merge(binance,interest,on=["Symbol"],how='outer')
interest = pd.merge(coinbase,interest,on=["Symbol"],how='outer')
interest = pd.merge(ledn,interest,on=["Symbol"],how='outer')
interest = pd.merge(cdc,interest,on=["Symbol"],how='outer')

#===============================================================================
# Merge it all together
#===============================================================================
print("Write")
# Finalize order
interest = interest[['Coin', 'Symbol', 'Binance.US', 'BlockFi', 'Crypto.com', 'Celsius', 'Coinbase', 'Gemini', 'Ledn', 'Nexo', 'Voyager']]
interest = interest.fillna('–')
interest = interest.replace('–', '')

interest = interest.sort_values('Symbol')

nan_value = float("NaN")
interest.replace("", nan_value, inplace=True)
interest = interest.dropna(subset=['Binance.US', 'BlockFi', 'Crypto.com', 'Celsius', 'Coinbase', 'Gemini', 'Ledn', 'Nexo', 'Voyager'], how='all')
interest = interest.fillna('')

interest.to_csv('interest.csv')

# Final filter
interest = interest[['Symbol', 'Binance.US', 'BlockFi', 'Celsius', 'Coinbase', 'Gemini', 'Ledn']]
nan_value = float("NaN")
interest.replace("", nan_value, inplace=True)
interest = interest.dropna(subset=['Binance.US', 'BlockFi', 'Celsius', 'Coinbase', 'Gemini', 'Ledn'], how='all')
interest = interest.fillna('')

################################################################################
# 12. Add to Crypto Sheets
################################################################################
# From: https://erikrood.com/Posts/py_gsheets.html

#authorization
#interest.to_csv('interest.csv', index=False)




