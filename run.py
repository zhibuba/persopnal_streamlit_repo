import os
import sys

# get python path
python_path = os.path.abspath(sys.executable)

# get streamlit path
script_streamlit = os.path.join(os.path.dirname(python_path), r'streamlit.cmd')

# my script
current_dir = os.path.dirname(os.path.abspath(__file__))
script_webserver = os.path.join(current_dir, r'WebServer.py')

# Here is the magic to execute  "streamlit run WebServer.py"
sys.argv = [script_streamlit, "run", script_webserver]
exec(open(script_streamlit).read())