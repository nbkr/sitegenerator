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

def render_article():
    pass

def main(args):
    # Read the articles yml file
    with open('articles.yml', 'r') as f:
        data = yaml.safe_load(f)

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

        # Convert the Markdown to HTML
        html = markdown_to_html(markdown)
        print(html)

        # Render the article

        # Add the article to the list of articles for rendering of the index file.
        pass




parser = argparse.ArgumentParser(description="Ben's Homepage Generator")
parser.add_argument('--version', '-v', help='show version and exit', action='store_true')

args = parser.parse_args()

if args.version:
    print_version()
    sys.exit(0)

main(args)
