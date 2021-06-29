#!/usr/bin/env python3
import xml.etree.ElementTree as ET
from datetime import datetime as dt
from zipfile import ZipFile
import argparse
import os
import shutil


# Reformat payload ISO format dates to human readable format
def formattimestamp(instring):
	timestamp = dt.fromisoformat(instring[:-1])
	outstring = timestamp.strftime("%H:%M %d/%m/%Y")
	return(outstring)

# Include payload manifest in output
def manifest_output(infolder):
	manifest_tree = ET.parse(infolder + '/manifest.xml')
	manifest_root = manifest_tree.getroot()

	tab_output("Payload Manifest Info")
	println()

	for element in manifest_root.findall('.'):
	    utc_date =element.find('UTCDate').text
	    manifest_date = element.find('Date').text
	    product = element.find('Product').text
	    product_ver = element.find('ProductVersion').text
	    product_deploy_date =  element.find('ProductDeployUTCDate').text

	    tab_output("Manifext UTC Date:", formattimestamp(utc_date))
	    tab_output("Manifext Local Date:", manifest_date)
	    tab_output("Product:", product)
	    tab_output("Product Version:", product_ver)
	    tab_output("Product Deployment Date:", formattimestamp(product_deploy_date))

# Extract all the contents of zip file in different directory
def explode_payload(infile, infolder):
	with ZipFile(infile, 'r') as zipObj:
	   zipObj.extractall(infolder)
	   if not quiet_flag:
		   print('INFO: File is unzipped into folder:')
		   print(infolder)
		   print('*' * 75)

# Blow away temporary folder created to explode payload files.
def remove_temp_payload_dir(infolder):
	shutil.rmtree(infolder, ignore_errors=False, onerror=None)
	if not quiet_flag:
		print('\n')
		print('*' * 75)
		print('INFO: Deleted temporary folder:')
		print(infolder)

# Format and output lines, either to screen or both screen + file
def tab_output(instring, inval = "", width = 30):
	out_string = "{} {}".format(instring.ljust(width), inval)
	if output_flag:
		outfile = open(output_file, 'a')
		outfile.write(out_string + "\n")
		outfile.close
	if not quiet_flag:
		print(out_string)

# Print separator line
def println(inchar = "-", width = 75):
	tab_output(inchar * width)

def main():
	parser = argparse.ArgumentParser()
	parser.add_argument('-p', '--payload', required=True, help="Payload file to parse.")
	parser.add_argument('-o', '--output-to-file', action='store_true', help="Store parsed output to file as well as echoed to screen.")
	parser.add_argument('-u', '--users', action='store_true', help="Include active users for each user billable SKU.")
	parser.add_argument('-a', '--all-skus', action='store_true', help="Include SKUs that aren't billable.")
	parser.add_argument('-s', '--serial-numbers', action='store_true', help="Include license serial numbers.")
	parser.add_argument('-l', '--license-server-plaform', action='store_true', help="Include License Server Platform details.")
	parser.add_argument('-m', '--manifest', action='store_true', help="Include manifest data in output.")
	parser.add_argument('-q', '--quiet', action='store_true', help="Quieten output. Only really makes sense if used with the -o/--output-to-file switch.")
	args = parser.parse_args()

	basedir = os.path.dirname(os.path.abspath(args.payload))
	payloadname = os.path.splitext(os.path.basename(args.payload))[0] 
	temp_folder = os.path.join(basedir,payloadname)

	global quiet_flag
	if args.quiet:
		quiet_flag = True
	else:
		quiet_flag = False

	global output_flag
	if args.output_to_file:
		output_flag = True
		global output_file
		output_file = temp_folder + ".txt"
		print('Output file: ' + payloadname + ".txt")
		println('*')	
	else:
		output_flag = False	

	explode_payload(args.payload, temp_folder)

	header_date = dt.utcfromtimestamp(int(payloadname[-10:])).strftime('%d/%m/%Y')
	tab_output(('Payload file: ' + payloadname + '.zip'), ('dated ' + header_date))
	println('*')

	tree = ET.parse(temp_folder + '/report.xml')
	root = tree.getroot()

	tab_output("\nLicense Server Info")
	println()
	for lsinfo in root.findall('./LSInfo'):
		# Reporting Organisation Details
		orgid = lsinfo.find('OrgID').text
		customerid = lsinfo.find('CustomerID').text
		reportdate = formattimestamp(lsinfo.find('DateSampleStopUTC').text)

		# LS Details
		fqdn = lsinfo.find('FQDN').text
		guid = lsinfo.find('GUID').text
		lsver = lsinfo.find('ProductVersion').text
		privsetting = lsinfo.find('PrivacySetting').text

		# Output LS Details
		tab_output("OrgID:", orgid)
		tab_output("CustomerID:", customerid)
		tab_output("Report Date", reportdate)

		tab_output("\nLS Details:")
		tab_output("  FQDN:", fqdn)
		tab_output("  GUID:", guid)
		tab_output("  LS Version:", lsver)
		tab_output("  Anonymised:", privsetting)
        
        # Include License Server Platform details, if -l flag set
		if args.license_server_plaform:
			# LS Platform Details
			windowsplatform = lsinfo.find('WindowsProductName').text
			windowsver = lsinfo.find('OS').text
			cpuid = lsinfo.find('CPUIDString').text.strip()
			vmid = lsinfo.find('VMIDString').text
			hwid = lsinfo.find('HardwareId').text
			
			# Output LS Platform Details
			tab_output("\nLS Platform Details:")
			tab_output("  Platform:", windowsplatform)
			tab_output("  Windows Ver:", windowsver)
			tab_output("  CPU Type:", cpuid)
			tab_output("  VM ID:", vmid)
			tab_output("  Hardware ID:", hwid)


	tab_output("\nUsage Report")
	println()
	for feature in root.findall('./Inventory/Feature'):
		feature_id = feature.find('ID').text
		sa_date = feature.find('SADate').attrib
		
		if feature_id == 'CITRIX' or feature_id == 'CTXLSDIAG' or feature_id == 'PVSD_STD_CCS':
			# Include non chargable SKUs, if -a flag set
			if args.all_skus:
				tab_output("\nProduct:", feature_id)
				tab_output("  SA Date:", sa_date.get('id'))
				for report in feature.findall('SADate'):
					period_start_date = formattimestamp(report.find('DateSampleStartUTC').text)
					period_end_date = formattimestamp(report.find('DateSampleStopUTC').text)
					tab_output("  Period from:", period_start_date)
					tab_output("  to:", period_end_date)

		# Output charagble SKU info
		elif feature_id == 'XDT_PLT_UD' or feature_id == 'XDT_ADV_UD':
			report_date = formattimestamp(feature.find('UDReportGenerationUTC').text)
			tab_output("\nProduct:", feature_id)
			tab_output("  SA Date:", sa_date.get('id'))
			tab_output("  Report Date:", report_date)
			
			for report in feature.findall('SADate'):
				period_start_date = formattimestamp(report.find('DateSampleStartUTC').text)
				period_end_date = formattimestamp(report.find('DateSampleStopUTC').text)
				max_used = report.find('CountUsedMax').text
				billable_users = report.find('CountUsersBillable').text
				count_installed = report.find('CountInstalled').text

				tab_output("  Period from:", period_start_date)
				tab_output("            to:", period_end_date)
				tab_output("  Active Users:", max_used)
				tab_output("* Charged Users:", billable_users)
				tab_output("  Installed:", count_installed)

				# Include active user info, if -u flag set
				if args.users:
					tab_output("\nActive Users:")
					if privsetting == 'Off':
						# Users not anonymised
						for user in root.findall('./Inventory/Feature/SADate/UsersBillable/ID'):
							lastlogon = formattimestamp(user.attrib['timeLastLogin'])
							tab_output(("  " + lastlogon),  user.text, 25)
					else:
						# Anonymised users
						tab_output("  Users anonymised")

		else:
			tab_output("Unknown FeatureId:", feature_id)

	# Include serial number info, if -s flag set
	if args.serial_numbers:
		tab_output("\nSerial Numbers")
		println()
		for serialnumbers in root.findall('./SerialNumbers'):
			for serial in serialnumbers:
				serial_id = serial.find('ID').text
				tab_output("Product: " + serial_id)
				for sn in serial.findall('SN'):
					tab_output("  " + sn.text)
				tab_output('\n')

	# Include manifest info, if -m flag set
	if args.manifest:
		manifest_output(temp_folder)

	remove_temp_payload_dir(temp_folder)

if __name__ == "__main__":
	main()