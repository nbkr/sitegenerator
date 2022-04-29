#! /usr/bin/env python3

import sys
import yaml
import argparse
import jinja2
import mistletoe
import os
import shutil
import subprocess
import logging

CONFIGCACHE=None

def get_version():
    return '1.1.0'

def print_version():
    print(get_version())

def markdown_to_html(markdown):
    return mistletoe.markdown(markdown)

def title_to_path(title):
    title = title.lower()
    title = title.replace(' ', '-')
    return title

def get_first_heading(markdown):
    lines = markdown.split("\n")
    for l in lines:
        if l.startswith('# '):
            return l.replace('# ', '').strip()

def check_if_in_config(args, key):
    global CONFIGCACHE
    if CONFIGCACHE is None:
        if not os.path.exists(args.configfile):
            logging.critical('Configfile at "{}" does not exist.'.format(args.configfile))
            sys.exit(1)
        try:
            with open(args.configfile, 'r') as f:
                config = yaml.safe_load(f)
                CONFIGCACHE = config
        except:
            logging.critical('Could not open configfile at "{}".'.format(args.configfile))
            sys.exit(1)
    else:
        config = CONFIGCACHE


    c = config
    found = True
    for k in key.split('.'):
        if k in c:
            c = c[k]
        else:
            found = False

    return found

def get_config(args, key):
    global CONFIGCACHE
    if CONFIGCACHE is None:
        if not os.path.exists(args.configfile):
            logging.critical('Configfile at "{}" does not exist.'.format(args.configfile))
            sys.exit(1)
        try:
            with open(args.configfile, 'r') as f:
                config = yaml.safe_load(f)
                CONFIGCACHE = config
        except:
            logging.critical('Could not open configfile at "{}".'.format(args.configfile))
            sys.exit(1)
    else:
        config = CONFIGCACHE


    c = config
    for k in key.split('.'):
        if k in c:
            c = c[k]
        else:
            logging.critical('Config key "{}" not set properly.'.format(key))
            sys.exit(1)

    return c

def set_logging(loglevel, logfile):
    # Setting the loglevel
    numeric_level = getattr(logging, args.loglevel.upper(), None)
    handlers = []
    handlers.append(logging.StreamHandler(sys.stdout))
    if args.logfile is not None:
        handlers.append(logging.FileHandler(args.logfile))

    logging.basicConfig(
            format='%(asctime)s - %(levelname)s - %(message)s',
            level=numeric_level,
            handlers=handlers
        )

def main_version(args):
    print_version()
    sys.exit(0)

def main_sync(args):
    set_logging(args.loglevel, args.logfile)

    logging.info('Starting rsync.')
    try:
        subprocess.check_call('rsync -az --delete {}/ {}'.format(get_config(args, 'builddir'), get_config(args, 'sync.{}.dest'.format(args.environment))), shell=True)
    except:
        logging.critical('Rsync failed.')
        sys.exit(1)

    logging.info('rsync done.')

def get_vars(articleconfig, globalarticleconfig, globalvar):
    ret = {}


    if articleconfig is not None:
        for k in articleconfig:
            ret[k] = articleconfig[k]

    if 'var' in globalarticleconfig:
        if globalarticleconfig['var'] is not None:
            for k in globalarticleconfig['var']:
                ret[k] = globalarticleconfig['var'][k]

    if globalvar is not None:
        for k in globalvar:
            ret[k] = globalvar[k]

    return ret


def main_generate(args):

    set_logging(args.loglevel, args.logfile)

    logging.info('Starting site generation.')

    # Read the articles yml file
    data = get_config(args, 'articles')

    if data is None:
        logging.critical('No articles defined.')
        sys.exit(1)

    if os.path.exists(get_config(args, 'builddir')):
        logging.debug('Removing the build folder.')
        shutil.rmtree(get_config(args, 'builddir'))

    if os.path.exists(get_config(args, 'staticdir')):
        logging.debug('Copying the general static folder to the build folder.')
        shutil.copytree('{}/'.format(get_config(args, 'staticdir')), '{}/'.format(get_config(args, 'builddir')))

    if not os.path.exists(get_config(args, 'builddir')):
        logging.debug('Creating the build folder.')
        os.makedirs(get_config(args, 'builddir'))

    # Template environment
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(get_config(args, 'templatesdir'), encoding='utf8'))

    articlelist = []

    for article in data:
        logging.debug('Processing article with source "{}".'.format(article['source']))
        logging.debug('Clearing the temp folder')
        # Create/Empty Temp folder
        if os.path.exists('temp'):
            shutil.rmtree('temp')

        os.makedirs('temp')

        # Download the article from the git repository into a temp folder
        logging.debug('Calling git clone for "{}"'.format(article['source']))
        try:
            subprocess.check_call('git clone --quiet {} temp 2>&1 >/dev/null'.format(article['source']), shell=True)
        except:
            print('FAILED: git clone {}'.format(article['source']))
            sys.exit(1)

        # Read the text file
        if not os.path.exists('temp/text.md'):
            logging.critical('temp/text.md does not exist for source "{}"'.format(article['source']))
            sys.exit(1)

        with open('temp/text.md', 'r') as f:
            markdown = f.read()

        # Read the config file
        if not os.path.exists('temp/var.yml'):
            logging.critical('temp/var.yml does not exist for source "{}"'.format(article['source']))
            sys.exit(1)

        with open('temp/var.yml', 'r') as f:
            articleconfig = yaml.safe_load(f)

        globalvar = None
        if check_if_in_config(args, 'var'):
            globalvar = get_config(args, 'var')

        var = get_vars(articleconfig, article, globalvar)

        # Get the title
        if 'title' not in var:
            var['title'] = get_first_heading(markdown)
            logging.debug('Getting var.title "{}" from first header.'.format(var['title']))

        # We generate the path from the title if it isn't provided by the 
        # article itself.
        if 'path' not in var:
            var['path'] = title_to_path(var['title'])
            logging.debug('Generating path "{}" from title.'.format(var['path']))

        # Copy the contents of the 'static' folder build folder
        if os.path.exists('temp/static'):
            logging.debug('Copying static folder from article.')
            shutil.copytree('temp/static/', '{}/{}/'.format(get_config(args, 'builddir'), var['path']))


        # Convert the Markdown to Jinja2 to HTML
        logging.debug('Converting Markdown to HTML.')
        contentenv = jinja2.Environment(loader=jinja2.BaseLoader).from_string(markdown)
        try:
            markdown = contentenv.render(var=var)
        except:
            logging.critical('Rendering of text.md of source "{}" to markdown failed.'.format(article['source']))
            sys.exit(1)
        html = markdown_to_html(markdown)
        
 
        # Render the article with the template it wants - with limits.
        logging.debug('Rendering article.')
        default_template = 'article.html'
        valid_templates = ['article.html', 'article_raw.html']
        if 'template' not in var:
            template = default_template
        elif not os.path.exists('{}/{}'.format(get_config(args, 'templatesdir'), var['template'])) or var['template'] not in valid_templates:
            logging.warning('Invalid template file "{}" for article "{}". Fallback to default template "article.html".'.format(var['template'], var['title']))
            template = default_template
        else:
            template = var['template']
        template = env.get_template(template)


        try:
            article = template.render(
                                        content=html,
                                        var=var
                                        )
        except:
            logging.critical('Rendering of source "{}" to article failed.'.format(article['source']))
            sys.exit(1)

        # Safe the page to the build folder.
        if not os.path.exists('{}/{}'.format(get_config(args, 'builddir'), var['path'])):
            logging.debug("Creating the articles folder inside the build folder.")
            os.makedirs('{}/{}'.format(get_config(args, 'builddir'), var['path']))

        with open('{}/{}/index.html'.format(get_config(args, 'builddir'), var['path']), 'w') as k:
            logging.debug("Writing the articles index.html")
            k.write(article)


        # Add the article to the list of articles for rendering of the index file.
        # You can set 'index: false' in the articles config file to exclude the article from the index page.
        if 'index' not in var or var['index'] == True:
            logging.debug('Adding article "{}" to the index.'.format(var['title']))
            articlelist.append({'title': var['title'],
                                'path': var['path']})

    # Create the index
    logging.debug("Creating the index.")
    template = env.get_template('index.html')
    index = template.render(
                            articles=articlelist,
                            var=var
                            )
    with open('{}/index.html'.format(get_config(args, 'builddir')), 'w') as k:
        k.write(index)

    if os.path.exists('temp'):
        logging.debug("Removing temp dir")
        shutil.rmtree('temp')

    logging.info("Site generation complete.")

parser = argparse.ArgumentParser(description="Ben's Homepage Generator.")
parser.add_argument('--loglevel', help='Setting the loglevel.', choices=['critical', 'error', 'warning', 'info', 'debug'], default='INFO')
parser.add_argument('--logfile', help='Output logs to given logfile.')
parser.add_argument('--configfile', '-c', help='Where to find the configfile.', default='config.yml')


subparsers = parser.add_subparsers()
sub_gen = subparsers.add_parser('generate', aliases=['gen'], description='Generate the site.', help='Generate the site.')
sub_gen.set_defaults(func=main_generate)

sub_version = subparsers.add_parser('version', aliases=['v'], description='Show version and exit.', help='Show version and exit.')
sub_version.set_defaults(func=main_version)

sub_sync = subparsers.add_parser('sync', description='Sync build folder to environment.', help='Sync build folder to environment.')
sub_sync.add_argument('environment', help='The environment within config.yml to sync to.')
sub_sync.set_defaults(func=main_sync)

args = parser.parse_args()
if 'func' in args:
    args.func(args)
else:
    parser.parse_args(['--help'])
