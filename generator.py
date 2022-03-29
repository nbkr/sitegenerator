import sys
import yaml
import argparse
import jinja2
import mistletoe
import os
import shutil
import subprocess
import logging

def get_version():
    return '1.0.0'

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

def render_article():
    pass

def main(args):

    # Setting the loglevel
    numeric_level = getattr(logging, args.loglevel, None)
    handlers = []
    handlers.append(logging.StreamHandler(sys.stdout))
    if args.logfile is not None:
        handlers.append(logging.FileHandler(args.logfile))

    logging.basicConfig(
            format='%(asctime)s - %(levelname)s - %(message)s',
            level=numeric_level,
            handlers=handlers
        )

    logging.info('Starting site generation.')

    # Read the articles yml file
    with open('articles.yml', 'r') as f:
        data = yaml.safe_load(f)

    if os.path.exists('build'):
        logging.debug('Removing the build folder.')
        shutil.rmtree('build')

    if os.path.exists('static'):
        logging.debug('Copying the general static folder to the build folder.')
        shutil.copytree('static/', 'build/')

    if not os.path.exists('build'):
        logging.debug('Creating the build folder.')
        os.makedirs('build')

    # Template environment
    env = jinja2.Environment(loader=jinja2.FileSystemLoader('templates', encoding='utf8'))

    articlelist = []

    for article in data:
        logging.debug('Processing article.')
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
        if not os.path.exists('temp/config.yml'):
            logging.critical('temp/config.yml does not exist for source "{}"'.format(article['source']))
            sys.exit(1)

        with open('temp/config.yml', 'r') as f:
            config = yaml.safe_load(f)

        # Get the title
        if 'title' in config:
            title = config['title']
            logging.debug('Getting title "{}" from config.'.format(title))
        else:
            title = get_first_heading(markdown)
            logging.debug('Getting title "{}" from first header.'.format(title))

        # We generate the path from the title if it isn't provided by the 
        # article itself.
        if 'path' not in config:
            path = title_to_path(title)
            logging.debug('Generating path "{}" from title.'.format(path))
        else:
            path = config['path']
            logging.debug('Taking path "{}" from config.'.format(path))

        # Copy the contents of the 'static' folder build folder
        if os.path.exists('temp/static'):
            logging.debug('Copying static folder from article.')
            shutil.copytree('temp/static/', 'build/{}/'.format(path))

        # Convert the Markdown to HTML
        logging.debug('Converting Markdown to HTML.')
        html = markdown_to_html(markdown)
 
        # Render the article with the template it wants - with limits.
        logging.debug('Rendering article.')
        default_template = 'article.html'
        valid_templates = ['article.html', 'article_raw.html']
        if 'template' not in config:
            template = default_template
        elif not os.path.exists('templates/{}'.format(config['template'])) or config['template'] not in valid_templates:
            logging.warning('Invalid template file "{}" for article "{}". Fallback to default template "article.html".'.format(config['template'], title))
            template = default_template
        else:
            template = config['template']
        template = env.get_template(template)
        article = template.render(
                                    content=html,
                                    config=config
                                    )

        # Safe the page to the build folder.
        if not os.path.exists('build/{}'.format(path)):
            logging.debug("Creating the articles folder inside the build folder.")
            os.makedirs('build/{}'.format(path))

        with open('build/{}/index.html'.format(path), 'w') as k:
            logging.debug("Writing the articles index.html")
            k.write(article)


        # Add the article to the list of articles for rendering of the index file.
        # You can set 'index: false' in the articles config file to exclude the article from the index page.
        if 'index' not in config or config['index'] == True:
            logging.debug('Adding article "{}" to the index.'.format(title))
            articlelist.append({'title': title,
                                'path': path})

    # Create the index
    logging.debug("Creating the index.")
    template = env.get_template('index.html')
    index = template.render(
                            articles=articlelist
                            )
    with open('build/index.html', 'w') as k:
        k.write(index)

    logging.info("Site generation complete.")

parser = argparse.ArgumentParser(description="Ben's Homepage Generator")
parser.add_argument('--version', '-v', help='show version and exit', action='store_true')
parser.add_argument('--loglevel', help='Setting the loglevel.', choices=['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'], default='INFO')
parser.add_argument('--logfile', help='Output logs to given logfile.')

args = parser.parse_args()

if args.version:
    print_version()
    sys.exit(0)

main(args)
