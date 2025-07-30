import asyncio as aio
from email.message import EmailMessage
from email.utils import make_msgid, formataddr
import smtplib
import warnings

try:
	import aiosmtplib
except ImportError:
	aiosmtplib = None


def _build(subject, plain_text, from_name, from_email, from_full=None, to_addrs=None, cc_addrs=None, reply_to=None, html_content=None):
	msg = EmailMessage()
	msg['Subject'] = subject
	msg['From'] = from_full if from_full else formataddr((from_name, from_email))
	msg['To'] = ', '.join(to_addrs or [])
	if cc_addrs:
		msg['Cc'] = ', '.join(cc_addrs)
	if reply_to:
		msg['Reply-To'] = reply_to
	msg['Message-ID'] = make_msgid()
	msg['X-Priority'] = '3'
	msg['X-Mailer'] = 'Python EmailSender'
	msg.set_content(plain_text)
	if html_content:
		msg.add_alternative(html_content, subtype='html')
	return msg


def _send(recipients, msg, smtp_server, smtp_port, smtp_protocol, smtp_user, smtp_password):
	server_cls = smtplib.SMTP_SSL if smtp_protocol == 'ssl' else smtplib.SMTP
	with server_cls(smtp_server, smtp_port) as server:
		if smtp_protocol == 'starttls':
			server.starttls()
		server.login(smtp_user, smtp_password)
		server.send_message(msg, to_addrs=recipients)


async def _send_async(recipients, msg, smtp_server, smtp_port, smtp_protocol, smtp_user, smtp_password):
	await aiosmtplib.send(
		message=msg,
		recipients=recipients,
		hostname=smtp_server,
		port=smtp_port,
		username=smtp_user,
		password=smtp_password,
		use_tls=smtp_protocol == 'ssl',
		start_tls=smtp_protocol == 'starttls'
	)


def _infer_email_address(user, server):
	if '@' in user:
		return user
	domain = '.'.join(filter(lambda x: x in ('smtp', 'mail', 'mx', 'email', 'imap'), server.lower().split('.')))  # Remove common SMTP nonsense
	return f'{user}@{domain}'


def send_email(smtp_server, smtp_user, smtp_password, to_emails=None, cc_emails=None, bcc_emails=None, reply_to=None, subject='', plain_text='', html_content=None, smtp_port=465, smtp_protocol=None, from_name='', from_email='', from_full=None, send_individually=False, asynchronous=True):
	"""
	Send an email with support for To, CC, BCC, and optional individual sending.

	Parameters
	----------
	smtp_server : str
		Hostname or IP address of the SMTP server (e.g., 'smtp.gmail.com').
	smtp_user : str
		Username for SMTP authentication (usually the sender's email).
	smtp_password : str
		Password or app-specific password for SMTP authentication.
	from_email : str
		Email address that will appear in the "From" field.
	to_emails : List[str], optional
		List of recipient email addresses.
	cc_emails : List[str], optional
		List of CC (carbon copy) email addresses.
	bcc_emails : List[str], optional
		List of BCC (blind carbon copy) email addresses.
	subject : str, default=''
		Subject line of the email.
	plain_text : str, default=''
		Plain-text version of the email body.
	html_content : str, optional
		HTML version of the email body. If provided, the email will be sent as multipart/alternative.
	smtp_port : int, default=465
		Port number for SMTP (typically 465 for SSL, 587 for STARTTLS).
	smtp_protocol : str, optional
		Security protocol for SMTP. Can be 'ssl' or 'starttls', ''. If None, defaults to SSL if port 465, STARTTLS if port 587, '' otherwise.
	from_name : str, default=''
		Display name that will appear in the "From" field.
	from_full : str, optional
		Override the "From" field with a custom value.
	send_individually : bool, default=False
		If True, send one email per recipient (To + CC + BCC each get a separate message).
	asynchronous : bool, default=True
		Use aiosmtplib for asnychronous sending.
	"""
	to_emails = to_emails or []
	cc_emails = cc_emails or []
	bcc_emails = bcc_emails or []

	all_recipients = list(set(to_emails + cc_emails + bcc_emails))

	# Determine SMTP protocol if not provided
	if smtp_protocol is None:
		smtp_protocol = 'ssl' if smtp_port == 465 else 'starttls' if smtp_port == 587 else ''
	smtp_protocol = smtp_protocol.lower()

	# Determine FROM info automatically if not provided
	if from_full is None:
		if not from_email:
			from_email = _infer_email_address(smtp_user, smtp_server)
		if not from_name:
			from_name = smtp_user.split('@')[0].replace('.', ' ').title()

	if asynchronous and not aiosmtplib:
		warnings.warn("aiosmtplib is not installed. Falling back to synchronous sending.")
		asynchronous = False
	asynchronous = asynchronous and send_individually  # No point in async if just sending one email

	if send_individually:
		msgs = []
		for to_recipient in to_emails:
			# To list: single TO recipient
			to_list = [to_recipient]
			# Cc list: all CC recipients
			cc_list = cc_emails if cc_emails else []
			# Build email message with one TO, full CC, no BCC in headers
			msg = _build(subject, plain_text, from_name, from_email, from_full, to_list, cc_list, reply_to, html_content)
			# Recipients for SMTP envelope include TO, CC, and BCC
			smtp_recipients = list(set(to_list + cc_list + bcc_emails))
			msgs.append((msg, smtp_recipients))
	else:
		msg = _build(subject, plain_text, from_name, from_email, from_full, to_emails, cc_emails, reply_to, html_content)
		msgs = [(msg, all_recipients)]

	if asynchronous:
		async def _send_all():
			tasks = [_send_async(recipients, msg, smtp_server, smtp_port, smtp_protocol, smtp_user, smtp_password) for msg, recipients in msgs]
			await aio.gather(*tasks)
		return aio.run(_send_all())

	for msg, recipients in msgs:
		_send(recipients, msg, smtp_server, smtp_port, smtp_protocol, smtp_user, smtp_password)
