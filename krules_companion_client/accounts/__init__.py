from typing import Annotated, List
import string
import secrets

import typer
from rich.console import Console
from rich import print
import firebase_admin
from firebase_admin import credentials, auth

app = typer.Typer()

err_console = Console(stderr=True)


def generate_password():
    letters = string.ascii_letters
    digits = string.digits
    special_chars = string.punctuation
    selection_list = letters + digits + special_chars
    password_len = 16
    password = ''
    for i in range(password_len):
        password += ''.join(secrets.choice(selection_list))
    return password


@app.command()
def create(
        email: Annotated[str, typer.Argument(help="user email")],
        subscription: Annotated[List[str], typer.Option(
            "-s", "--subscription", help="User subscription (can be more than one)", envvar="COMPANION_SUBSCRIPTION")
        ] = (),
        password: Annotated[
            str, typer.Option(
                "-p", "--password", help="User password. If not specified a random one will be created")] = "",
        service_account: Annotated[
            str, typer.Option(
                "-sa", "--service-account", help="Firebase service account path")] = "",
        project: Annotated[
            str, typer.Option(
                "-p", "--project", help="Firebase project id. If service account is set this value will be ignored",
                envvar="GOOGLE_CLOUD_PROJECT")] = "",
):
    if service_account:
        options = None
        if project:
            options = {"projectId": project}
        firebase_admin.initialize_app(credentials.Certificate(service_account), options=options)
    else:
        if project:
            firebase_admin.initialize_app(options={"projectId": project})
        else:
            firebase_admin.initialize_app()

    if not password:
        password = generate_password()

    new_user = auth.create_user(email=email, email_verified=True, password=password)

    if subscription:
        auth.set_custom_user_claims(
            new_user.uid,
            {
                'active_subscription': subscription[0],
                'subscriptions': subscription
            }
        )

    print(f"USER_UID: {new_user.uid}\nEMAIL: {new_user.email}\nPASSWORD: {password}\nSUBSCRIPTIONS: {subscription}")
