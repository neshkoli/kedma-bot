# Kedma Bot

![Kedma Bot](kedma_bot.png)

Kedma Bot is an AI-powered bot that publishes daily posts to a Telegram channel about significant events in Jewish history that occurred on the current Hebrew date.

## Features

- **Daily Posts**: Automatically generates and posts content daily.
- **Hebrew Date**: Uses the Hebrew calendar to determine the date.
- **Jewish History**: Provides historical events related to the current Hebrew date.
- **Telegram Integration**: Posts are published directly to a specified Telegram channel.

## Installation

1. Clone the repository:

    ```sh
    git clone https://github.com/neshkoli/kedma-bot.git
    cd kedma-bot
    ```

2. Create a virtual environment and activate it:

    ```sh
    python3 -m venv venv
    source venv/bin/activate
    ```

3. Install the required dependencies:

    ```sh
    pip install -r requirements.txt
    ```

4. Create a `.env` file in the project directory and add your Telegram bot token and DeepSeek API key:

    ```env
    TELEGRAM_BOT_TOKEN=your_telegram_bot_token
    DEEPSEEK_API_KEY=your_deepseek_api_key
    ```

## Usage

1. Run the bot:

    ```sh
    python JewishHistoryBot.py
    ```

2. The bot will automatically generate and post content to the specified Telegram channel daily.

## Configuration

<img src="https://www.iconfinder.com/icons/1419139/download/png/128" alt="Telegram" width="64" height="64"/> 

- **Telegram Bot Token**: Set your Telegram bot token in the `.env` file.

<img src="https://storage.top100token.com/images/0ec73a40-b314-42ac-8d11-7d28503c4367.webp" alt="DeepSeek" width="64" height="64"/> 

- **DeepSeek API Key**: Set your DeepSeek API key in the `.env` file.


## Contributing

1. Fork the repository.
2. Create a new branch (`git checkout -b feature-branch`).
3. Make your changes.
4. Commit your changes (`git commit -am 'Add new feature'`).
5. Push to the branch (`git push origin feature-branch`).
6. Create a new Pull Request.

## License

This project is licensed under the MIT License. See the [LICENSE](http://_vscodecontentref_/1) file for details.

## Acknowledgements

- Inspired by the rich history of the Jewish people.
- Uses the Hebrew calendar for date calculations.
- Built with love and respect for historical accuracy.
