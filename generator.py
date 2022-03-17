import sys
import yaml
import argparse
import jinja2
import mistletoe
import os
import shutil
import subprocess

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

def render_article():
    pass

def main(args):
    # Read the articles yml file
    with open('articles.yml', 'r') as f:
        data = yaml.safe_load(f)

    if os.path.exists('build'):
        shutil.rmtree('build')

    if os.path.exists('static'):
        shutil.copytree('static/', 'build/')

    if not os.path.exists('build'):
        os.makedirs('build')

    # Template environment
    env = jinja2.Environment(loader=jinja2.FileSystemLoader('templates', encoding='utf8'))

    articlelist = []

    for article in data:
        # Create/Empty Temp folder
        if os.path.exists('temp'):
            shutil.rmtree('temp')

        os.makedirs('temp')

        # Download the article from the git repository into a temp folder
        try:
            subprocess.check_call('git clone --quiet {} temp 2>&1 >/dev/null'.format(article['source']), shell=True)
        except:
            print('FAILED: git clone {}'.format(article['source']))
            sys.exit(1)

        # Read the text file
        if not os.path.exists('temp/text.md'):
            print('FAILED: temp/text.md does not exist.')
            sys.exit(1)

        with open('temp/text.md', 'r') as f:
            markdown = f.read()

        # Read the config file
        if not os.path.exists('temp/config.yml'):
            print('FAILED: temp/config.yml does not exist.')
            sys.exit(1)

        with open('temp/config.yml', 'r') as f:
            config = yaml.safe_load(f)

        # Get the title
        title = config['title']
        path = title_to_path(title)

        # Copy the contents of the 'static' folder build folder
        if os.path.exists('temp/static'):
            shutil.copytree('temp/static/', 'build/{}/'.format(path))

        # Convert the Markdown to HTML
        html = markdown_to_html(markdown)
 
        # Render the article
        template = env.get_template('article.html')
        article = template.render(
                                    content=html,
                                    config=config
                                    )

        # Safe the page to the build folder.
        if not os.path.exists('build/{}'.format(path)):
            os.makedirs('build/{}'.format(path))

        with open('build/{}/index.html'.format(path), 'w') as k:
            k.write(article)



        # Add the article to the list of articles for rendering of the index file.
        articlelist.append({'title': title,
                            'path': path})

    # Create the index
    template = env.get_template('index.html')
    index = template.render(
                            articles=articlelist
                            )
    with open('build/index.html', 'w') as k:
        k.write(index)


parser = argparse.ArgumentParser(description="Ben's Homepage Generator")
parser.add_argument('--version', '-v', help='show version and exit', action='store_true')

args = parser.parse_args()

if args.version:
    print_version()
    sys.exit(0)

main(args)
