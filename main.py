import os
import re
import smtplib
from email.message import EmailMessage

import pandas as pd
import requests
from bs4 import BeautifulSoup

year = ''
month = ''

def perform_web_scraping(url):
  # Setting up the output directory for data:
  global extracted_date, year, month, day, save_path
  directory = "TGE_daily"
  parent_dir = os.path.dirname(__file__)
  path = os.path.join(parent_dir, directory)
  os.makedirs(path, exist_ok=True)
  
  # Send an HTTP GET request
  response = requests.get(url)
  
  if response.status_code == 200:
      # Parse the HTML content
      soup = BeautifulSoup(response.text, 'html.parser')
    
      # Finding the date related to prices:
      date_section = soup.find('h4', class_='kontrakt-date')  
      if date_section:
          # Extract the date information
          date_str = date_section.find('small').text.strip()
          # Use a regular expression to extract the date pattern
          match = re.search(r'\b\d{1,2}-\d{1,2}-\d{4}\b', date_str)  
          if match:
              extracted_date = match.group()
              year = extracted_date[6:]
              month = extracted_date[3:5]
              day = extracted_date[0:2]
          else:
              print("Date not found in the string.")
  
      # Find the table with the specified class
      table = soup.find('table', class_='footable table table-hover table-padding')  
      if table:
          # Find all rows in the table body
          rows = table.select('tbody tr')
          data_list = []  
          for row in rows:
              # Find all cells in the row
              cells = row.find_all('td')  
              # Extract and print or process the cell data
              row_data = [cell.text.strip() for cell in cells]
              data_list.append(row_data)
          
          # Preparing a DF for data deployment:
          column_names = ['Czas', 'Fixing 1 - Kurs (PLN/MWh}', 'Fixing 1- Wolumen [MWh]', 'Fixing 2 - Kurs (PLN/MWh}', 'Fixing 2- Wolumen [MWh]', 'NC - Kurs (PLN/MWh}', 'NC- Wolumen [MWh]']
          df = pd.DataFrame(data_list, columns=column_names)
          df.insert(0, 'Data', extracted_date)

          # Save the DataFrame to a CSV file in subdirectories based on year and month
          save_directory = os.path.join(path, year, month)
          os.makedirs(save_directory, exist_ok=True)
          save_path = os.path.join(save_directory, f'{extracted_date}.csv')
          df.to_csv(save_path, index=False)
          
          # Use the date as the file name
          save_path = os.path.join(path, f'{extracted_date}.csv')
          # Save the DataFrame to a CSV file
          df.to_csv(save_path, index=False)
      else:
          print("Table not found on the webpage.")
  
  else:
    print("The TGE website couldn't be reached.")

def aggregate_month():
  # Function which will aggregate the RDN data for each month
  global monthly_data_file
  directory = fr'{os.getcwd()}/TGE_daily/{year}/{month}'
  files_this_month = (os.listdir(directory))
  files = [os.path.join(directory, file) for file in files_this_month if file.endswith('.csv')]
  
  # Read and concatenate CSV files
  df_list = [pd.read_csv(file) for file in files]
  combined_df = pd.concat(df_list, ignore_index=True)
  combined_df[['Start', 'End']] = combined_df['Czas'].str.split('-', expand=True)
  combined_df['Start'] = pd.to_numeric(combined_df['Start'])
  combined_df['End'] = pd.to_numeric(combined_df['End'])
  sorted_df = combined_df.sort_values(by=['Data', 'Start', 'End'], ascending=[True, True, True])
  sorted_df = sorted_df.drop(['Start', 'End'], axis=1)

  
  # Save the combined DataFrame to a new CSV file
  output_folder = "Monthly_Summary"
  output_file = f'{year}-{month}.csv'
  monthly_data_file = os.path.join(os.getcwd(), output_folder, output_file)
  os.makedirs(os.path.join(os.getcwd(), output_folder), exist_ok=True)
  sorted_df.to_csv(monthly_data_file, index=False)
  
def email_files(email_recipent):
  # Prepairing email:
  msg = EmailMessage()
  msg['From'] = 'tge.odczyty@ogarnij.se'
  msg['To'] = f'{email_recipent}'
  msg['Subject'] = f'Dane z TGE {extracted_date}'

  # Attach the daily file
  daily_file_path = os.path.join(os.getcwd(), 'TGE_daily', f'{extracted_date}.csv')
  with open(daily_file_path, 'rb') as daily_file:
      msg.add_attachment(daily_file.read(), maintype='application', subtype='octet-stream', filename=f"{extracted_date}.csv")

  # Attach the monthly file
  monthly_file_path = os.path.join(os.getcwd(), 'Monthly_Summary', f'{year}-{month}.csv')
  with open(monthly_file_path, 'rb') as monthly_file:
      msg.add_attachment(monthly_file.read(), maintype='application', subtype='octet-stream', filename=f"{year}-{month}.csv")

  try:
    with smtplib.SMTP('poczta.interia.pl', 587) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.login('tge.odczyty@ogarnij.se', 'GreenVoltPower123!')
        smtp.send_message(msg)
        print(f"Data from {extracted_date} sent via email to wojtek.maniak@gmail.com")
  except Exception as e:
    print(f"Error sending email: {e}")

# URL where the TGE is publishing prices
url = "https://tge.pl/energia-elektryczna-rdn"

# Email recipents
# email_recipents = ['wojciech.maniak@greenvolt.com', 'damian.artyszak@greenvolt.com']

perform_web_scraping(url)
aggregate_month()

# for person in email_recipents:
  # email_files(person)

