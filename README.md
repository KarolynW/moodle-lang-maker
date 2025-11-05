Moodle Language Pack Maker

1. Configure paths in config.py
   MOODLE_CODE_ROOT: your Windows checkout, eg C:\moodle

2. Create a virtual environment and install deps
   py -3 -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt

3. Set credentials
   For OpenAI:
     set OPENAI_API_KEY=sk-...
   For Azure OpenAI:
     set AZURE_OPENAI_ENDPOINT=https://<your-endpoint>.openai.azure.com
     set AZURE_OPENAI_API_KEY=...
     set AZURE_OPENAI_DEPLOYMENT=<your-deployment-name>

4. Run all steps
   py src\run_all.py

5. Result
   output\en_variant_by_component\
   output\en_variant_by_sourcefile\

6. Test on Linux
   Pick one of the two output folders, rename it to en_skyrim,
   copy to /var/www/moodledata/lang/en_skyrim
   Then purge caches in Site administration.
