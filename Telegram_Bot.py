import requests


class Telegram:
    """
    A class for sending text messages using the Telegram Bot API.
    """

    def __init__(
        self,
        token='***************************',
        chat_id='#########',
        message='target detected'
    ):
        """
        Initialize the Telegram sender object.

        Parameters
        ----------
        token : str
            Telegram bot token.

        chat_id : str
            Telegram chat ID.

        message : str
            Message text to send.
        """
        self.token = token
        self.chat_id = chat_id
        self.message = message

        # Base API endpoint for Telegram sendMessage method
        self.url = f"https://api.telegram.org/bot{self.token}/sendMessage"

    def send_message(self):
        """
        Send the message to Telegram.

        Returns
        -------
        dict
            Telegram API response in JSON format.
        """
        # Parameters sent with the request
        params = {
            "chat_id": self.chat_id,
            "text": self.message
        }

        # Send request to Telegram API
        response = requests.get(self.url, params=params)

        # Return parsed JSON response
        return response.json()