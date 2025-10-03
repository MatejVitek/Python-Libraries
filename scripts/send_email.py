#!/usr/bin/env python3
# USAGE: python send_email.py RECIPIENT_EMAIL [RECIPIENT_EMAIL ...] -f BODY_FILE [OPTIONS]
# Keep in mind that many SMTP providers require app-specific passwords, 2FA, or other security measures.
# For Gmail specifically, you need to:
# - enable 2FA;
# - create an app password (https://myaccount.google.com/apppasswords);
# - use that app password as the SMTP password.

import getpass
from html.parser import HTMLParser
import os
import re

from matej.argparse import ArgParser, StrArg
from matej.web.email import send_email


class EmailArg(StrArg):
	EMAIL_RE = re.compile(r'[\w\.-]+@[\w\.-]+\.[\w-]+')

	def _type(self, s):
		s = super()._type(s)
		if s is None:
			return None
		if not self.EMAIL_RE.fullmatch(s):
			from argparse import ArgumentTypeError
			raise ArgumentTypeError(f"'{s}' is not a valid email address.")
		return s


def parse_cli_args():
	ap = ArgParser(description="Send an email via SMTP.")
	ap.add_arg(EmailArg('emails', help="Addresses of the recipients", nargs='*'))
	ap.add_path_arg('-f', '--file', help="Path to file containing the email body", required=True)
	ap.add_path_arg('-a', '--attachment', '--attachments', help="Path(s) to file(s) to attach", nargs='+')
	ap.add_str_arg('-s', '--subject', help="Email subject")
	ap.add_str_arg('-u', '--user', help="SMTP login username")
	ap.add_str_arg('-p', '--password', help="SMTP password (for increased security, set it in the environment variable SMTP_PASSWORD or leave empty to get prompted securely)")
	ap.add_str_arg('-S', '--server', help="SMTP server address", default='smtp.gmail.com')
	ap.add_number_arg('-P', '--port', help="SMTP server port", nargs=1, default=465, min=0)
	ap.add_choice_arg(['SSL', 'STARTTLS', ''], '--protocol', help="SMTP security protocol", nullable=True)
	ap.add_str_arg('-e', '--from-email', help="Sender email address")
	ap.add_str_arg('-n', '--from-name', help="Sender display name")
	ap.add_str_arg('-F', '--from-full', help="Override 'From' field with custom value")
	ap.add_arg(EmailArg('-r', '--reply-to', help="Reply-To email address"))
	ap.add_arg(EmailArg('-c', '--cc', help="CC emails (will be added on each email if sending individually)", nargs='+'))
	ap.add_arg(EmailArg('-b', '--bcc', help="BCC emails (will be added on each email if sending individually)", nargs='+'))
	ap.add_bool_arg('-i', '--send-individually', help="Send emails to each recipient separately", default=True)
	ap.add_number_arg('-l', '--limit', '--rate-limit', help="Rate limit (in emails per second)", nargs=1, min=0)
	return ap.parse_args()


class HTMLStripper(HTMLParser):
	def __init__(self):
		super().__init__()
		self.reset()
		self.fed = []

	def handle_data(self, data):
		self.fed.append(data)

	def get_data(self):
		return ''.join(self.fed)


def strip_html(html):
	stripper = HTMLStripper()
	stripper.feed(html)
	return stripper.get_data()


def detect_html(content):
	content = content.lower()
	return (
		'<html' in content or
		'<body' in content or
		'<div' in content or
		'<p' in content
	)


def main():
	args = parse_cli_args()

	# Validate recipients
	if not args.emails and not args.cc and not args.bcc:
		raise ValueError("At least one recipient email address is required (To, CC, or BCC).")

	# SMTP username prompt (with repeat on empty)
	while not args.user:
		args.user = input("SMTP username (email): ").strip()
		if not args.user:
			print("SMTP username cannot be empty. Please try again.")

	# SMTP password prompt (from env or prompt)
	args.password = args.password or os.getenv('SMTP_PASSWORD')  # Check if password is saved in environment variable
	while not args.password:
		args.password = getpass.getpass("SMTP password: ").strip()
		if not args.password:
			print("Password cannot be empty.")

	# Load content
	if not args.file.exists():
		raise ValueError(f"File not found: {args.file}")
	if not args.subject:
		args.subject = args.file.stem
	raw = args.file.read_text(encoding='utf-8')
	if args.file.suffix.lower() in ('.html', '.htm') or detect_html(raw):
		plain_text = strip_html(raw)
		html = raw
	else:
		plain_text = raw
		html = None

	# Send the email
	send_email(
		smtp_server=args.server,
		smtp_port=args.port,
		smtp_protocol=args.protocol,
		smtp_user=args.user,
		smtp_password=args.password,
		from_email=args.from_email,
		from_name=args.from_name,
		from_full=args.from_full,
		reply_to=args.reply_to,
		to_emails=args.emails,
		cc_emails=args.cc,
		bcc_emails=args.bcc,
		subject=args.subject,
		plain_text=plain_text,
		html_content=html,
		attachments=args.attachment,
		send_individually=args.send_individually,
		rate_limit=args.limit,
	)


if __name__ == "__main__":
	main()