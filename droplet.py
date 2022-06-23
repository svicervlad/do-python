'''
Controll remote dev server

* Requires:
 - DIGITALOCEAN_ACCESS_TOKEN
 - MY_RESERVED_IP
'''
import os
from time import sleep
import digitalocean
import click


DROPLET = 'remote-dev'
CLOUD_INIT_DEFAULT_TEMPLATE = f'{DROPLET}.yaml'
MY_RESERVED_IP = os.environ.get('MY_RESERVED_IP')

manager = digitalocean.Manager()


@click.group()
def cli():  # pylint: disable=missing-function-docstring
    pass


def load_cloud_template(name):
    '''
    Load template for cloud init
    '''
    with open(f'templates/{name}', 'r', encoding='utf-8') as f:  # pylint: disable=invalid-name
        return f.read()


def get_droplet(name):
    '''
    Get droplet by name
    '''
    my_droplets = manager.get_all_droplets(
    )  # type: list[digitalocean.Droplet]
    for droplet in my_droplets:
        if droplet.name == name:
            return droplet
    return None


@cli.command(name='get-droplet')
@click.argument('name')
def get_droplet_cmd(name):
    '''
    Get droplet by name
    '''
    droplet = get_droplet(name)
    if droplet:
        click.echo(f'Droplet {droplet.name} found')
        click.echo(f'Droplet id: {droplet.id}')
        click.echo(f'Droplet ip: {droplet.ip_address}')
        click.echo(f'Droplet status: {droplet.status}')
        click.echo(f'Droplet region: {droplet.region["name"]}')
        click.echo(f'Droplet created at: {droplet.created_at}')
        click.echo(f'Droplet networks: {droplet.networks["v4"]}')
        click.echo(f'Droplet tags: {droplet.tags}')
    else:
        click.echo(f'Droplet {name} not found')


def destroy_droplet(name):
    '''
    Destroy droplet by name
    '''
    droplet = get_droplet(name)
    if droplet:
        droplet.destroy()
        return droplet


@cli.command(name='destroy-droplet')
@click.argument('name')
def destroy_droplet_cmd(name):
    '''
    Destroy droplet by name
    '''
    droplet = destroy_droplet(name)
    if droplet:
        click.echo(f'Droplet {droplet.name} destroyed')
    else:
        click.echo(f'Droplet {name} not found')


def create_droplet(
    name: str = DROPLET,
    region: str = 'fra1',
    size_slug: str = "s-2vcpu-4gb",
    image: str = "ubuntu-22-04-x64",
    user_data: str = None,
    tags: list = []
):  # pylint: disable=dangerous-default-value,too-many-arguments
    '''
    Create droplet
    '''
    droplet = digitalocean.Droplet(
        token=manager.token,
        name=name,
        region=region,
        image=image,
        size_slug=size_slug,
        backups=False,
        monitoring=True,
        ipv6=False,
        ssh_keys=manager.get_all_sshkeys(),
        user_data=user_data,
        tags=tags
    )
    droplet.create()
    return droplet


@cli.command(name='create-droplet')
@click.argument('name', default=DROPLET)
@click.argument('region', default='fra1')
@click.argument('size_slug', default='s-2vcpu-4gb')
@click.argument('image', default='ubuntu-22-04-x64')
@click.argument('template', default=CLOUD_INIT_DEFAULT_TEMPLATE)
@click.argument('tags', default=[])
def create_droplet_cmd(name, region, size_slug, image, template, tags):
    '''
    Create droplet
    '''
    user_data = load_cloud_template(template)
    droplet = create_droplet(name, region, size_slug, image, user_data, tags)
    click.echo(f'Droplet {droplet.name} created')


@cli.command(name='rebuild-dev-server')
def rebuild_remote_dev_server():
    '''
    Rebuild remote-dev server
    '''
    droplet = get_droplet(DROPLET)
    if droplet:
        click.echo(f'Droplet {DROPLET} already exists, destoing it')
        droplet.destroy()
    click.echo(f'Creating droplet {DROPLET}')
    clound_init = load_cloud_template(CLOUD_INIT_DEFAULT_TEMPLATE)
    droplet = create_droplet(name=DROPLET, region='fra1', size_slug='s-2vcpu-4gb',
                             image='ubuntu-22-04-x64', tags=['remote-dev'], user_data=clound_init)
    sleep(10)
    max_retries = 3
    retry_count = 0
    max_timewait = int(120 / 3)
    count_wait = 0
    while retry_count < max_retries or count_wait < max_timewait:
        count_wait += 1
        sleep(3)
        droplet = get_droplet(DROPLET)
        actions = droplet.get_actions()
        status = False
        if retry_count == 1:
            click.echo('Waiting for droplet to be ready')
        for action in actions:
            if action.type == 'create' and action.status == 'completed':
                status = True
        if status:
            retry_count += 1
            try:
                ip = digitalocean.FloatingIP(   # pylint: disable=invalid-name
                    token=manager.token,
                    ip=MY_RESERVED_IP
                ).load()
                ip.assign(droplet_id=droplet.id)
            except (digitalocean.baseapi.DataReadError, digitalocean.baseapi.NotFoundError):
                click.echo(
                    f'Retry assign reserved ip {retry_count}/{max_retries}')
                click.echo(f'Droplet {droplet.name} not completed yet or ip not found')
                click.echo(f'Droplet id: {droplet.id}')
                sleep(5)
            else:
                click.echo(f'Droplet {DROPLET} created')
                click.echo(f"Droplet ip: {MY_RESERVED_IP}")
                break


@cli.command(name='destroy-dev-server')
def destroy_remote_dev_server():
    '''
    Destroy remote-dev server
    '''
    droplet = get_droplet(DROPLET)
    if droplet:
        click.echo(f'Droplet {DROPLET} already exists, destoing it')
        droplet.destroy()
    click.echo(f'Droplet {DROPLET} destroyed')


if __name__ == '__main__':
    cli()
