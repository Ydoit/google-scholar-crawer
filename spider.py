import argparse
import datetime
import os
import sys
import time
import warnings
from dataclasses import dataclass
from time import sleep
from typing import List, Optional

import matplotlib.pyplot as plt
import pandas as pd
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm


# now = datetime.datetime.now()

'''as_vis=0: Including papers with few or no citations. 
    as_vis=1: Including papers with many citations.
    as_ylo: start year
    as_yli: end year
    as_sdt: 0,5: Search scope includes all articles, include citations 2007 for including patents.
    '''

BASE_URL='https://scholar.google.com/scholar?as_vis=0&as_sdt=0,5'
START_YEAR='&as_ylo{}'
END_YEAR='&as_yhi{}'
KEYWORD='&q={}'
HL='&hl={}'
SORT_BY_DATE='&scisbd=1'
START='&start={}'
ROBORT_KW=['unusual traffic from your computer network', 'not a robot']
CURRENT_YEAR=datetime.datetime.now().year


@dataclass
class SearchConfig:
    keyword: str="audio deepfake"
    num_resutls: int=100
    start_year: Optional[int]=2020
    end_year:int =CURRENT_YEAR
    hl: str="en"
    sortby: str="Citations"
    debug: bool=False
    save_path:str='./'
    file:str='googlescholar.csv'


def get_parser() -> SearchConfig:
    parser=argparse.ArgumentParser(description="Google Scholar Crawler")
    parser.add_argument('--keyword', type=str, default='audio deepfake', help='Keyword to search')
    parser.add_argument('--num_results', type=int, default=100, help='Number of results to return')
    parser.add_argument('--start_year', type=int, default=2020, help='Start year of search')
    parser.add_argument('--end_year', type=int, default=CURRENT_YEAR, help='End year of search')
    parser.add_argument('--hl', type=str, default='en', help='Language of search')
    parser.add_argument('--sortby', type=str, choices=['Citations', 'Date'], default='Citations', help='Sort by')
    parser.add_argument('--debug', type=bool, default=False, help='Debug mode')
    parser.add_argument('--save_path', type=str, default='./', help='Path to save the results')
    parser.add_argument('--file', type=str, default='googlescholar.csv', help='Filename to save the results')
    # parser.add_argument('--help', action='help', help='Show this help message and exit')
    
    args,_=parser.parse_known_args()
    # if args.help:
    #     parser.print_help()
    #     sys.exit()
    return SearchConfig(keyword=args.keyword if args.keyword else SearchConfig.keyword, 
                        num_resutls=args.num_results if args.num_results else SearchConfig.num_resutls, 
                        start_year=args.start_year if args.start_year else SearchConfig.start_year, 
                        end_year=args.end_year if args.end_year else SearchConfig.end_year, 
                        hl=args.hl, sortby=args.sortby if args.sortby else SearchConfig.sortby, 
                        debug=args.debug if args.debug else SearchConfig.debug, 
                        save_path=args.save_path if args.save_path else SearchConfig.save_path,
                        file=args.file if args.file else SearchConfig.file) 




def current_url(searchconfig: SearchConfig) -> str:
    url=BASE_URL
    if searchconfig.start_year< CURRENT_YEAR and searchconfig.start_year<searchconfig.end_year:
        url+=START_YEAR.format(searchconfig.start_year)
    if searchconfig.end_year>=CURRENT_YEAR:
        url+=END_YEAR.format(CURRENT_YEAR)
    else :
        url+=END_YEAR.format(searchconfig.end_year)
    if searchconfig.sortby=='Date':
        url+=SORT_BY_DATE
    url+=KEYWORD.format(searchconfig.keyword.replace(' ', '+'))
    return url


def get_authors(authorstr: str) -> str:
    authors=authorstr.split('-')[0]
    return authors


def get_citiations(citationstr: str) -> int:
    try:
        citation=citationstr.split('Cited by ')[-1].split(' ')[0]
    except:
        citation=0
    return int(citation)

def fetch_data(searchconfig: SearchConfig, session:requests.Session,url:str,pbar:Optional[tqdm]) -> pd.DataFrame:
    links: List[str]=[]
    titles: List[str]=[]
    authors: List[str]=[]
    citations: List[int]=[]
    years: List[int]=[]
    venues: List[str]=[]
    publishers: List[str]=[]
    # ranks: List[int]=[0]
    descriptions: List[str]=[]
    
    if pbar is not None:
        pbar.set_description('Fetching data')   
        pbar.reset(total=searchconfig.num_resutls)
    for i in range(0, searchconfig.num_resutls, 10):
        if pbar is not None:
            pbar.update(10)
        
        page=session.get(url+START.format(i))
        content=page.content
        if any(kw in content.decode('ISO-8859-1') for kw in ROBORT_KW):
            warnings.warn('Blocked by Google. Please try again later.')
            continue
        soup=BeautifulSoup(content, 'html.parser',from_encoding='utf-8')
        resultdivs=soup.find_all('div', {'class':'gs_r gs_or gs_scl'})
        for div in resultdivs:
            
            try:
                link=div.find('h3', {'class':'gs_rt'}).find('a')['href']
            except:
                link='Can not find link,please check manually.'    
            try:
                title=div.find('h3', {'class':'gs_rt'}).find('a').text
            except:
                title='Can not find title, please check manually.'
            try:
                citation=get_citiations(div.find('div', {'class':'gs_fl gs_flb'}).text)
            except:
                citation=0
            try:
                author=get_authors(div.find('div', {'class':'gs_a'}).text)
            except:
                author='Can not find author, please check manually.'
            try:
                year=(int(div.find('div', {'class':'gs_a'}).text.split(',')[-1].split('-')[0].strip()))
            except:
                year='Can not find year, please check manually.'
            try:
                publisher=div.find('div', {'class':'gs_a'}).text.split('-')[-1].strip()
            except:
                publisher='Can not find publisher, please check manually.'
            try:
                venue=div.find('div', {'class':'gs_a'}).text.split('-')[-2].strip()
            except:
                venue='Can not find venue, please check manually.'
            try:
                description=div.find('div', {'class':'gs_rs'}).text
            except:
                description='Can not find description, please check manually.'
            links.append(link)
            titles.append(title)
            authors.append(author)
            citations.append(citation)
            years.append(year)
            venues.append(venue)
            publishers.append(publisher)
            descriptions.append(description)
    data=pd.DataFrame({'Title':titles, 'Authors':authors, 'Citations':citations, 'Year':years, 'Venue':venues, 'Publisher':publishers, 'Description':descriptions, 'Link':links})
    return data  
                
                
        


def crawler(searchconfig: SearchConfig):
    url=current_url(searchconfig)
    if searchconfig.debug:
        print(url)
    session=requests.Session() 
    page=requests.get(url)
    if any(kw in page.content.decode('ISO-8859-1') for kw in ROBORT_KW):
        warnings.warn('Blocked by Google. Please try again later.')
        with open('robort.html','w',encoding='utf-8') as f:
            f.write(page.content.decode('ISO-8859-1'))
        return
    soup=BeautifulSoup(page.content, 'html.parser')
    with tqdm(total=searchconfig.num_resutls) as pbar:
        data=fetch_data(searchconfig, session, url, pbar)
    data.to_csv(os.path.join(searchconfig.save_path,searchconfig.file), index=False)
    
    
if __name__=='__main__':
    print('Crawler started.')
    print('-------------------------------------------')
    start_time=time.time()
    searchconfig=get_parser()
    crawler(searchconfig)
    end_time=time.time()
    use_time=end_time-start_time
    print('-------------------------------------------')
    print('Crawler finished.')
    print('Time used: {:.2f}s'.format(use_time))