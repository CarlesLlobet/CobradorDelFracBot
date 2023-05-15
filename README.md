# Cobrador del Frac Bot

Simple dockerized python Telegram Bot to remind your colleagues to pay their debts.

## Requirements
- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/get-started/08_using_compose/#install-docker-compose)

## Getting Started

### Telegram Bot creation

The only configuration required in order to get started is to create a .env file with your Telegram Token (`TELEGRAM_TOKEN`).

If you don't have a Telegram Token yet, you'll need one through Telegram's BotFather.
See details on Bot creation [here](https://core.telegram.org/bots/features#botfather).

### Configuration

Now that we have a Telegram Token for our bot, the configuration is as easy as:
```
$ echo "TELEGRAM_TOKEN=0123456789:AbCd1e2f3G..." > .env
```

### Usage

#### Deployment
To deploy this Bot in your own environment after configuring the Telegram Token, you just have to execute:

```
$ docker-compose up -d
```

## Built With

* [Python](https://www.python.org/) - The programming language that lets you work quickly and integrate systems more effectively.

## Authors

* **Carles Llobet** - *Complete work* - [Github](https://github.com/CarlesLlobet)

See also the list of [contributors](https://github.com/CarlesLlobet/CobradorDelFracBot/contributors) who participated in this project.

## Acknowledgments

* Project inspired by https://github.com/CarlosLugones/python-telegram-bot-docker