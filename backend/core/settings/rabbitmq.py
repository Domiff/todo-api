from core.settings.env import env

RABBITMQ = {
    "USER": env("RABBITMQ_USER"),
    "PASSWORD": env("RABBITMQ_PASSWORD"),
    "HOST": env("RABBITMQ_HOST"),
    "PORT": env("RABBITMQ_PORT"),
}

RABBITMQ_URL = (
    f"amqp://{RABBITMQ['USER']}:{RABBITMQ['PASSWORD']}"
    f"@{RABBITMQ['HOST']}:{RABBITMQ['PORT']}//"
)
