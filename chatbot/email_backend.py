"""
Custom email backend that bypasses SSL certificate verification for development.
This is needed on macOS where SSL certificate verification often fails.
"""
import ssl
import smtplib
from django.core.mail.backends.smtp import EmailBackend as SMTPEmailBackend


class SSLEmailBackend(SMTPEmailBackend):
    """
    Custom email backend that bypasses SSL certificate verification.
    Only use this for development/testing purposes.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure all required attributes are set
        if not hasattr(self, 'local_hostname'):
            self.local_hostname = None
    
    def open(self):
        """
        Ensure we have a connection to the email server. Return whether or not a
        new connection was required (True or False).
        """
        if self.connection:
            # Nothing to do if the connection is already open.
            return False

        # Create unverified SSL context for development
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        # If local_hostname is not specified, socket.getfqdn() gets used.
        connection_params = {}
        if self.local_hostname:
            connection_params['local_hostname'] = self.local_hostname
            
        try:
            if self.use_ssl:
                # Use SSL connection with unverified context
                self.connection = smtplib.SMTP_SSL(
                    self.host, self.port, context=context, **connection_params
                )
            else:
                # Use regular SMTP connection
                self.connection = smtplib.SMTP(
                    self.host, self.port, **connection_params
                )
                
                # Start TLS with unverified context if needed
                if self.use_tls:
                    self.connection.starttls(context=context)
                
            if self.username and self.password:
                self.connection.login(self.username, self.password)
                
            return True
        except (OSError, smtplib.SMTPException):
            if not self.fail_silently:
                raise