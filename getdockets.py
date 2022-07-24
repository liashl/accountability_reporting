from ast import Pass
from playwright.sync_api import sync_playwright
import pandas as pd
import tabula
import re
import requests
import PyPDF2
import time
import csv
from bs4 import BeautifulSoup
from datetime import datetime

import os
import base64

from google.oauth2 import service_account
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from email.mime.image import MIMEImage
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
import mimetypes

#reference table for charges
c_table = pd.read_csv('code_table.csv',encoding = 'unicode_escape')

def get_date_string():
    date_var = datetime.today().strftime('%Y-%m-%d')
    return date_var

#FUNCTION docket_search
#input: date string (format must be: 'YYYY-mm-dd'), county string (example: 'Allegheny')
#County must be in the state of Pennsylvania.
#saves HTML of search page in current directory
#output: name of file containing HTML of website (contains search results) in current directory

def docket_search (search_date,county):
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=False)
        page = browser.new_page()

        #navigate to the search page
        page.goto("https://ujsportal.pacourts.us/CaseSearch")
        page.wait_for_timeout(5000)
        #page.screenshot(path="example.png")

        #identify element
        new_selector = '//*[@id="SearchBy-Control"]/select'
        page.wait_for_selector(new_selector)
        handle = page.query_selector(new_selector)

        #print inner HTML to check
        #print(handle.inner_html())
        print('searching by date...')

        #identify start date element
        handle.select_option("DateFiled")
        page.wait_for_timeout(2000)

        date_select1 = '//*[@id="FiledStartDate-Control"]/input'
        page.wait_for_selector(date_select1)

        #enter start date for search
        page.fill(date_select1,search_date)

        #identify end date element
        date_select2 = '//*[@id="FiledEndDate-Control"]/input'
        page.wait_for_selector(date_select2)

        #enter end date for search
        page.fill(date_select2, search_date)
        page.wait_for_timeout(2000)
        print(f'date range is {search_date} to {search_date}...')

        #identify the 'advance' radio button
        adv_select = '//*[@id="AdvanceSearch-Control"]/input'
        page.wait_for_selector(adv_select)
        page.check(adv_select)
        page.wait_for_timeout(2000)

        county_select = '//*[@id="County-Control"]/select'
        page.wait_for_selector(county_select)
        handle2 = page.query_selector(county_select)
        handle2.select_option(county)
        print('county is {}...'.format(county))

        page.wait_for_timeout(2000)

        bt = '//*[@id="btnSearch"]'
        page.wait_for_selector(bt)
        btsubmit = bt+'#submit'
        page.click(bt)
        
        page.wait_for_timeout(5000)

        #save content of table for future scraping

        mypage = page.content()
        #print(mypage)

        ofilename = f'{county}-{search_date}.txt'

        with open(ofilename,'w') as outfile:
            outfile.write(mypage)

        browser.close()

        return ofilename

#FUNCTION process_search uses BeautifulSoup to mine the docket information from html saved by the docket_search function.
#input is filename for the HTML that was saved off of website by docket_search function
#county is the name of the county for which we are examining court records. This is used only to generate the name of the file.
#This function saves the data as a CSV and returns the filename.

def process_search(ofilename,county):

    with open(ofilename,'r') as r:
        pagetxt = r.read()

    soup = BeautifulSoup(pagetxt,'html.parser')

    categories = [
        'docket_num',
        'court_type',
        'case_caption',
        'case_status',
        'filing_date',
        'primary_participant',
        'dob',
        'county',
        'court_office',
        'otn',
        'complaint_num',
        'incident_num',
        'docket_link',
        'case_summary_link'
    ]

    csv_filename = f'{county}dockets.csv'

    with open(csv_filename,'w',newline='') as outfile:
        writer=csv.writer(outfile)
        writer.writerow(categories)

    with open(csv_filename,'a',newline='') as outfile:
        writer=csv.writer(outfile)

        table = soup.find_all('table')[2]
        rows = table.find_all('tr')

        for row in rows[1:]:

            rowinfo = row.attrs
            #print(rowinfo)

            duplicate_checker = False
            if rowinfo != {}:
                classinfo = rowinfo['class']
                #print(classinfo)
                if('duplicate-row' in classinfo):
                    duplicate_checker = True

            if not duplicate_checker:

                cells = row.find_all('td')

                try:
                    docket_num = cells[2].text.strip()
                except IndexError:
                    docket_num = ''
                    continue

                try:
                    court_type = cells[3].text.strip()
                except IndexError:
                    court_type = ''

                try:
                    case_caption = cells[4].text.strip()
                except IndexError:
                    case_caption = ''

                try:
                    case_status = cells[5].text.strip()
                except IndexError:
                    case_status = ''

                try:
                    filing_date = cells[6].text.strip()
                except IndexError:
                    filing_date = ''

                try:
                    primary_participant = cells[7].text.strip()
                except IndexError:
                    primary_participant = ''

                try:
                    dob = cells[8].text.strip()
                except IndexError:
                    dob = ''

                try:
                    county = cells[9].text.strip()
                except IndexError:
                    county = ''

                try:
                    court_office = cells[10].text.strip()
                except IndexError:
                    court_office = ''

                try:
                    otn = cells[11].text.strip()
                except IndexError:
                    otn = ''

                try:
                    complaint_num = cells[12].text.strip()
                except IndexError:
                    complaint_num = ''

                try:
                    incident_num = cells[13].text.strip()
                except IndexError:
                    incident_num = ''

                try:
                    linktags = cells[18].find_all('a')
                    docket_link=linktags[0]['href']
                    case_summary_link=linktags[1]['href']
                except IndexError:
                    docket_link = 'no link found'
                    case_summary_link = 'no link found'


                data_out = [
                    docket_num,
                    court_type,
                    case_caption,
                    case_status,
                    filing_date,
                    primary_participant,
                    dob,
                    county,
                    court_office,
                    otn,
                    complaint_num,
                    incident_num,
                    docket_link,
                    case_summary_link
                ]

                #print(data_out)

                writer.writerow(data_out)

    return csv_filename

#FUNCTION get_dataframe:
#Input: CSV file of docket data for a given county
#strips data to contain only criminal cases in magesterial district court, then returns a PANDAS dataframe

def get_dataframe(csv_file):

    #open today's cases in PANDAS dataframe
    df = pd.read_csv(csv_file)

    #modify relative links into full links
    df['docketlink_full'] = "https://ujsportal.pacourts.us" + df['docket_link']
    df['caselink_full'] = "https://ujsportal.pacourts.us" + df['case_summary_link']

    #limit to magisterial district court criminal dockets by searching for substrings '-CR-' and 'MJ-' in docket number
    df_cr = df.loc[df['docket_num'].str.contains("-CR-",case=True)].loc[df['docket_num'].str.contains('MJ-',case=True)]

    return df_cr



#FUNCTION get_dockets:
#Input: PANDAS dataframe of today's criminal dockets from magesterial district court in a given county
#If status_code is 200 in all cases, saves docket files (.pdf format) and returns True
#If another status code is generated, returns False immediately and breaks loop

def get_dockets(df_cr):

    #check if DataFrame is empty
    if df_cr.empty:
        print('DataFrame is empty!')
        return False

    #prepare to open links 
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.82 Safari/537.36'
    }

    for i, link in df_cr.iterrows():
        url = link['docketlink_full']

        r = requests.get(url, headers=headers)
        stat_code = r.status_code
        print(r.status_code)
        
        if r.status_code == 200:

            #sets docket number as file name and saves
            dckt = link['docket_num']
            tempfilename = f'{dckt}.pdf'

            with open(tempfilename,'wb') as f:
                f.write(r.content)
                print('Download complete')

        else:
            print('Error connecting. Unable to download')
            return False

        time.sleep(2.5)

    return True

def docket_parser(df_cr):


    charge_dict = {}

    for i, link in df_cr.iterrows():

        dckt = link['docket_num']
        tempfilename = f'{dckt}.pdf'
        #print(tempfilename)

        
        with open(tempfilename,'rb') as pdf:
                pdf_read = PyPDF2.PdfFileReader(pdf)
                pages = pdf_read.numPages
                #print(pages)

        

        #use tabula to scrape into single giant text string
        page_one = tabula.read_pdf(tempfilename,pages=1,encoding='utf-8',multiple_tables=True,lattice=True)
        if pages == 2:
            page_two = tabula.read_pdf(tempfilename,pages=2,encoding='utf-8',multiple_tables=True,lattice=True)

        table_string_one = page_one[0].to_string().replace(r'\r','\n')
        if pages == 2:
            table_string_two = page_two[0].to_string().replace(r'\r','\n')
        else:
            table_string_two = ''
        table_string_three = table_string_one + table_string_two

        #print(table_string_three)

        
        #find index for the end of the given label
        labels=['CASE INFORMATION','STATUS INFORMATION','CALENDAR EVENTS','CONFINEMENT','DEFENDANT INFORMATION','CASE PARTICIPANTS','BAIL','CHARGES','DOCKET ENTRY INFORMATION']

        indices = []
        for label in labels:
            locate = re.search(label,table_string_three)
            if locate != None:
                indices.append(locate.span()[0])
                indices.append(locate.span()[1])
        
        parts = [table_string_three[i:j] for i,j in zip(indices, indices[1:]+[None])]

        chunks = {}
        for part in parts:
            if part in labels:
                temp_label = part
            else:
                temp_chunk = part
                chunks[temp_label]=temp_chunk

        #create dataframe
        df_chunks= pd.DataFrame(list(chunks.items()),columns = ['label','content'])
        df_chunks = df_chunks.set_index('label')
        
        #create separate variables for different chunks
        try:
            case_info_chunk_raw = df_chunks.loc['CASE INFORMATION'].iloc[0]
        except KeyError:
            case_info_chunk_raw = ''
            pass

        try:
            status_information_chunk_raw = df_chunks.loc['STATUS INFORMATION'].iloc[0]
        except KeyError:
            status_information_chunk_raw = ''
            pass
        
        try:
            calendar_events_chunk_raw = df_chunks.loc['CALENDAR EVENTS'].iloc[0]
        except KeyError:
            calendar_events_chunk_raw = ''
            pass

        try:
            confinement_chunk_raw = df_chunks.loc['CONFINEMENT'].iloc[0]
        except KeyError:
            confinement_chunk_raw = ''
            pass

        try:
            defendant_information_chunk_raw = df_chunks.loc['DEFENDANT INFORMATION'].iloc[0]
        except KeyError:
            defendant_information_chunk_raw = ''
            pass

        try:
            case_participants_chunk_raw = df_chunks.loc['CASE PARTICIPANTS'].iloc[0]
        except KeyError:
            case_participants_chunk_raw = ''
            pass

        try:
            bail_chunk_raw = df_chunks.loc['BAIL'].iloc[0]
        except KeyError:
            bail_chunk_raw = ''
            pass

        try:
            charges_chunk_raw = df_chunks.loc['CHARGES'].iloc[0]
            #print(charges_chunk_raw)
        except KeyError as err:
            charges_chunk_raw = ''
            pass

        try:
            docket_entry_information_chunk_raw = df_chunks.loc['DOCKET ENTRY INFORMATION'].iloc[0]
        except KeyError:
            docket_entry_information_chunk_raw = ''
            pass

        
        split_string = re.split(r'(§.*§§)',charges_chunk_raw)
        #print(split_string)
        
        charges = []
        for strx in split_string[1:-1]:
            if (strx != ''):
                x = re.search(r'(§.*§§)',strx)
                if x != None:
                    charge = x.group()
                    charge_shorter = charge.split('-')[0]
                    charges.append(charge_shorter)

        #print(link['docket_num'])
        #print(charges)

        
        charge_codes = []
        if charges != []:
            for charge in charges:
                #print(charge)
                try:
                    nums = [int(k) for k in charge.split() if k.isdigit()][0]
                except IndexError:
                    nums = 0000 #this is essentially an error because it won't be read. TODO: implement better processing when reading the charge codes
                charge_codes.append(nums)


        tempkey = link['docket_num']
        #print(charge_codes)
        #df_cr.loc[i,'new']=charge_codes

        
        #convert to strings
        scharge_codes = []

        for code in charge_codes:
            scode = f'{code}'
            scharge_codes.append(scode)

        #reference table for plain english on charges
        find_results = []

        for scode in scharge_codes:

            try:
                find_result = c_table.loc[c_table['code_section'].str.contains(scode)].iloc[0]['description']
            except IndexError:
                if scode == '780':
                    find_result = 'Prohibited Acts'
                elif scode == '3802':
                    find_result = 'Driving Under The Influence'
                else:
                    find_result='xx'
            shorter = find_result.split('(')[0].split(':')[0].split('-')[0].split('/')[0]
            find_results.append(shorter)

        charge_tags_list = find_results
        #print(charge_tags_list)
        

        #store charges in a dictionary
        charge_dict[tempkey]=[charge_codes,charge_tags_list]
        #print(charge_dict)

        
        docket_number = link['docket_num']
        court_type_new = link['court_type']
        case_caption_new = link['case_caption']
        case_status_new = link['case_status']
        #primary_participant_new = link['primary_participant']
        dob_new = link['dob']
        county_new = link['county']
        court_office_new = link['court_office']
        docketlink_full_new = link['docketlink_full']

        outstring = f'{docket_number}\n{case_caption_new}\nCharges: \n{charges_chunk_raw}\n\n{court_type_new}\n{case_status_new}\n{dob_new}\n{county_new}\n{court_office_new}\n{docketlink_full_new}\n\n========\n'
        


        with open(f'dockets{get_date_string()}.txt','a',encoding='utf-8') as outfile:
            outfile.write(outstring)


        print(docket_number)
        print(case_caption_new)
        #print(primary_participant_new)
        print('CHARGES: ',end='',flush=True)
        print(*charge_codes,sep=', ', end='',flush=True)
        print(' (automated best guess: ',end='',flush=True)
        print(*charge_tags_list,sep=', ',end='',flush=True)
        print(')')
        print(court_type_new)
        print(case_status_new)
        print(dob_new)
        print(county_new)
        print(court_office_new)
        print(docketlink_full_new)
        print('====')
        

        df_cr['charges'] = df_cr['docket_num'].map(charge_dict)
        
        notable = False
        charges_to_search = charge_tags_list
        charge_keywords = ['homicide','aggravated','HOMICIDE','AGGRAVATED','Homicide','Aggravated']

        for ch in charges_to_search:
            if any(x in ch for x in charge_keywords):
                notable = True


        if notable:
            print(docket_number)
            print(case_caption_new)
            print(charges_to_search)
            print(docketlink_full_new)
            print('======')

            outstring_notable = f'{docket_number}\n{case_caption_new}\n{charges_to_search}\n{county_new}\n{docketlink_full_new}\n=====\n'


            with open(f'notable{get_date_string()}.txt','a',encoding='utf-8') as nfile:
                nfile.write(outstring_notable)

        if os.path.exists(tempfilename):
            os.remove(tempfilename)

    return df_cr

#SETTING SCOPE FOR EMAIL
# If modifying these scopes, delete the file token.json.
SCOPES = ['https://mail.google.com/']

def get_service():

    SERVICE_ACCOUNT_FILE = 'pa-court-info-service-key.json'
    creds = service_account.Credentials.from_service_account_file(
        filename=SERVICE_ACCOUNT_FILE,
        scopes=['https://mail.google.com/'],
        subject='admin@llauntz.com'
    )

    #creds = None
   # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    #if os.path.exists('token.json'):
    #    creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    #if not creds or not creds.valid:
    #    if creds and creds.expired and creds.refresh_token:
    #        creds.refresh(Request())
    #    else:
    #        flow = InstalledAppFlow.from_client_secrets_file(
    #            'credentials.json', SCOPES)
    #        creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
    #    with open('token.json', 'w') as token:
    #        token.write(creds.to_json())

    try:
        # Call the Gmail API
        #service = build('gmail', 'v1', credentials=creds)
        service_gmail = build('gmail', 'v1', credentials=creds)
        return service_gmail

    except HttpError as error:
        # TODO(developer) - Handle errors from gmail API.
        print(f'An error occurred: {error}')

def send_message(service,user_id,message):
    try:
        message = service.users().messages().send(userId=user_id, body=message).execute() #should return dictionary
        print('message ID: {}'.format(message['id']))
        return message
    except Exception as e:
        print('an error occured: {}'.format(e))
        return None

def create_message_with_attachment(sender, to, subject, body, file):
    message = MIMEMultipart()
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject

    msg = MIMEText(body)
    message.attach(msg)

    (content_type, encoding) = mimetypes.guess_type(file)

    if content_type is None or encoding is not None:
        content_type = 'application/octet-stream'

    (main_type, sub_type) = content_type.split('/',1)

    if main_type == 'text':
        with open(file, 'rb') as f:
            msg = MIMEText(f.read().decode('utf-8'), _subtype=sub_type)

    elif main_type == 'image':
        with open(file, 'rb') as f:
            msg = MIMEImage(f.read(), _subtype=sub_type)

    elif main_type == 'audio':
        with open(file,'rb') as f:
            msg = MIMEAudio(f.read(), _subtype=sub_type)

    else:
        with open(file,'rb') as f:
            msg = MIMEBase(main_type, sub_type)
            msg.set_payload(f.read())

    filename = os.path.basename(file)

    msg.add_header('Content-Disposition', 'attachment', filename=filename)
    message.attach(msg)

    raw_msg = base64.urlsafe_b64encode(message.as_string().encode('utf-8'))

    return {'raw': raw_msg.decode('utf-8')}

#MAIN CODE BEGINS HERE

def main():
    county_list = ['Allegheny','Beaver','Butler','Fayette','Washington','Westmoreland']
    #county_list = ['Fayette'] #for test
    #print(county_list)

    #SET THE COUNTY TO SEARCH AND DATE
    search_date = get_date_string() #grabs today's date to use
    #print(search_date)

    #CLEAR THE PREVIOUS DAY'S DOCKETS FILES TO EMAIL
    open(f'dockets{get_date_string()}.txt','w',encoding='utf-8').close()
    open(f'notable{get_date_string()}.txt','w',encoding='utf-8').close()

    for county in county_list:
    #    pass
        #CALL THE DOCKET SEARCH FUNCTION
        fname = docket_search(search_date,county)
        print('File is',fname)

        #CALL THE PROCESS SEARCH FUNCTION
        csv_name = process_search(fname,county)
        print('CSV file name is',csv_name)

        #CREATE PANDAS DATAFRAME AND NARROW DATA

    #for test purposes
    #docketfile_list = ['Alleghenydockets.csv','Beaverdockets.csv','Butlerdockets.csv','Fayettedockets.csv','Washingtondockets.csv','Westmorelanddockets.csv']

    #for docketfile in docketfile_list:
        df_cr = get_dataframe(csv_name) #change input to docketfile for test
    #    print(df_cr.head())

        #GET THE DOCKET SHEET USING REQUESTS.GET
        stat_check = get_dockets(df_cr)
        #print(f'stat_check is: {stat_check}')
        if stat_check:
            print(f'success with dockets for {county}') #change county to docketfile for test
        else:
            print(f'Error. Dockets for {county} not completed.') #change county to docketfile for test

        #PARSE DOCKETS, WRITE FILES, RETURN DATAFRAME WITH CHARGES
        if df_cr.empty:

            #DELETE TODAY'S HTML DOWNLOAD FOR THE COUNTY IN QUESTION
            if os.path.exists(fname):
                os.remove(fname)
            continue
        else:
            df_cr_charges = docket_parser(df_cr)
            #print(df_cr_charges)

            #DELETE TODAY'S HTML DOWNLOAD FOR THE COUNTY IN QUESTION
            if os.path.exists(fname):
                os.remove(fname)


    #send email
    attach_name = f'dockets{get_date_string()}.txt'
    body_name = f'notable{get_date_string()}.txt'


    service = get_service()
    user_id = 'me'
    sender = 'admin@llauntz.com'
    to = 'liahardin@gmail.com'
    subject = 'TEST: daily court dockets'

    with open(body_name,'r') as b:
        body_text = b.read()

    body = body_text
    file = attach_name

    #print(body)

    msg = create_message_with_attachment(sender, to, subject, body, file)
    send_message(service, user_id, msg)

    #DELETE FILES USED TO BUILD EMAIL
    if os.path.exists(attach_name):
        os.remove(attach_name)

    if os.path.exists(body_name):
        os.remove(body_name)

if __name__ == "__main__":
    main()