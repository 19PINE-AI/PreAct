#!/usr/bin/env python3
"""Build site/src/data/programs.js: real compiled programs for Android / Desktop /
Web, each shown as a runtime-execution simulator. Android + Web carry real
screenshots; Desktop is program-only (no recoverable screenshots).

- Android programs: matched from the chroma DBs to the 12 hand-captured
  AndroidWorld trajectories that already have screenshots in site/public/traj.
- Web programs: pulled from the chroma DBs; each has a source_trace_id whose
  screenshots live in traces/<id>/step_*.png and get copied + downscaled.
- Desktop programs: taken verbatim from the already-clean corpus.js.
"""
import sqlite3, json, glob, os, re, shutil
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, 'site')
PUB = os.path.join(SITE, 'public')

# ---------------------------------------------------------------- load programs
def load_all():
    progs = {}
    for db in sorted(glob.glob(os.path.join(ROOT, 'rag_db*'))):
        f = os.path.join(db, 'chroma.sqlite3')
        if not os.path.exists(f):
            continue
        try:
            con = sqlite3.connect(f); cur = con.cursor()
            cur.execute("SELECT string_value FROM embedding_metadata WHERE key='chroma:document'")
            for (v,) in cur.fetchall():
                d = json.loads(v); pid = d['metadata'].get('program_id')
                if not pid:
                    continue
                # prefer a copy that has a usable source trace
                if pid not in progs or (d['metadata'].get('source_trace_id') and not progs[pid]['metadata'].get('source_trace_id')):
                    progs[pid] = d
            con.close()
        except Exception:
            pass
    return progs

# ---------------------------------------------------------------- normalisers
def trim_url(u):
    if not u:
        return u
    return u.replace('http://localhost:7780', '').replace('http://localhost', '') or '/'

def short_xpath(xp):
    if not xp:
        return xp
    # compiled selectors carry " | " fallbacks; show the first, flag the rest
    if ' | ' in xp:
        first, *rest = xp.split(' | ')
        return f"{first.strip()}  (+{len(rest)} fallback{'s' if len(rest) > 1 else ''})"
    return xp

def web_verify(state):
    ver = state['verification']
    t = ver['type']
    if t == 'terminal_state':
        return 'task complete'
    if t == 'data_available':
        return 'value captured' + (f" → ${ver['data_key']}" if ver.get('data_key') else '')
    if t == 'expect_element':
        return short_xpath(ver.get('xpath') or 'element present')
    return t

def web_action(action):
    t = action['type']
    if t == 'action_navigate':
        return f"navigate {trim_url(action.get('text'))}"
    if t == 'action_click':
        return f"click {short_xpath(action.get('target'))}"
    if t == 'action_type':
        if action.get('parameter_name'):
            return f"type ${action['parameter_name']}"
        return f"type {json.dumps(action.get('text') or '')}"
    if t == 'action_keypress':
        return f"press {action.get('key')}"
    if t == 'inspect_text':
        tgt = short_xpath(action.get('target') or '')
        var = action.get('store_result_as')
        return f"read {tgt}" + (f" → ${var}" if var else '')
    if t == 'inspect_screenshot':
        return 'read the screen'
    if t == 'wait':
        return 'wait'
    if t == 'evaluate_condition':
        return f"check {action.get('expression') or ''}"
    return t

def normalize_web(d):
    m = d['metadata']
    states = [{'id': s['id'], 'desc': s['description'], 'verify': web_verify(s)} for s in d['states']]
    trans = [{'from': t['from_state'], 'to': t['to_state'], 'action': web_action(t['action'])} for t in d['transitions']]
    return {
        'task': m['task_description'],
        'app': m.get('application_context', ''),
        'params': m.get('parameters', []),
        'states': states,
        'transitions': trans,
        'trace': m.get('source_trace_id'),
    }

def normalize_android(d):
    """DB android programs use the same verification/action schema as web but with
    android selectors; normalize to a verify string + action string."""
    m = d['metadata']
    def averify(s):
        ver = s['verification']; t = ver['type']
        if t == 'terminal_state':
            return 'task complete'
        if t == 'data_available':
            return 'value captured'
        # expect_element on android: the xpath holds a resource-id / text selector
        return short_xpath(ver.get('xpath') or 'element present')
    def aaction(action):
        t = action['type']
        if t == 'action_click':
            return f"tap {short_xpath(action.get('target'))}"
        if t == 'action_long_press':
            return f"long-press {short_xpath(action.get('target'))}"
        if t == 'action_type':
            if action.get('parameter_name'):
                return f"type ${action['parameter_name']}"
            return f"type {json.dumps(action.get('text') or '')}"
        if t == 'action_keypress':
            return f"press {action.get('key')}"
        if t in ('open_app',):
            return f"open {action.get('text') or action.get('target') or ''}"
        if t == 'navigate_back':
            return 'back'
        if t == 'navigate_home':
            return 'home'
        if t == 'scroll':
            return f"scroll {action.get('direction') or ''}"
        if t == 'wait':
            return 'wait'
        if t == 'inspect_text':
            return f"read {short_xpath(action.get('target') or '')}"
        return t
    states = [{'id': s['id'], 'desc': s['description'], 'verify': averify(s)} for s in d['states']]
    trans = [{'from': t['from_state'], 'to': t['to_state'], 'action': aaction(t['action'])} for t in d['transitions']]
    return {'task': m['task_description'], 'app': m.get('application_context', ''),
            'params': m.get('parameters', []), 'states': states, 'transitions': trans}

# ---------------------------------------------------------------- screenshots
def list_traj_imgs(tid):
    """existing android screenshots in public/traj/<tid>, ordered."""
    d = os.path.join(PUB, 'traj', tid)
    if not os.path.isdir(d):
        return []
    files = sorted(f for f in os.listdir(d) if f.lower().endswith(('.jpg', '.png')))
    return [f"traj/{tid}/{f}" for f in files]

def copy_web_screens(prog_id, trace_id, max_w=560):
    """copy traces/<trace_id>/step_*.png → public/webtraj/<prog_id>/NN.jpg downscaled."""
    src = os.path.join(ROOT, 'traces', trace_id)
    if not os.path.isdir(src):
        return []
    steps = sorted(f for f in os.listdir(src) if re.match(r'step_\d+\.png$', f))
    if not steps:
        return []
    out_dir = os.path.join(PUB, 'webtraj', prog_id)
    os.makedirs(out_dir, exist_ok=True)
    rels = []
    for i, f in enumerate(steps, 1):
        try:
            im = Image.open(os.path.join(src, f)).convert('RGB')
            if im.width > max_w:
                h = round(im.height * max_w / im.width)
                im = im.resize((max_w, h), Image.LANCZOS)
            name = f"{i:02d}.jpg"
            im.save(os.path.join(out_dir, name), 'JPEG', quality=82)
            rels.append(f"webtraj/{prog_id}/{name}")
        except Exception as e:
            print('  ! img fail', f, e)
    return rels

# ---------------------------------------------------------------- android match
# (trajectory id, display name, goal-prefix used to find the compiled program)
TRAJ = [
    ("ContactsAddContact_inst0", "Add a contact", "Create a new contact for Emilia Gonzalez"),
    ("ClockTimerEntry_inst0", "Set a timer", "Create a timer with 14 hours"),
    ("CameraTakePhoto_inst0", "Take a photo", "Take one photo."),
    ("MarkorCreateNote_inst0", "Create a note", "Create a new note in Markor named brave_violin"),
    ("FilesDeleteFile_inst0", "Delete a file", "Delete the file 2023_09_01_strong_dog.mp3"),
    ("SimpleSmsSend_inst0", "Send a text message", "Send a text message"),
    ("SimpleCalendarAddOneEvent_inst0", "Add a calendar event", "create a calendar event on 2023"),
    ("AudioRecorderRecordAudio_inst0", "Record audio", "Record an audio clip using Audio Recorder app and save it."),
    ("MarkorEditNote_inst0", "Edit a note", "Edit note_6aamy.txt in Markor"),
    ("ClockStopWatchRunning_inst0", "Run the stopwatch", "Run the stopwatch."),
    ("BrowserMaze_inst0", "Solve a browser maze", "Open the file task.html"),
]

def find_android(progs, prefix):
    pl = prefix.lower()
    cands = [d for d in progs.values()
             if not d['metadata'].get('application_context', '').startswith('http')
             and pl in d['metadata'].get('task_description', '').lower()]
    if not cands:
        return None
    # prefer the one with the most states (richest compiled program)
    return max(cands, key=lambda d: len(d['states']))

# ---------------------------------------------------------------- web selection
# distinct families, chosen for variety + a healthy screenshot count.
WEB_PICKS = [
    ("number of reviews that mention the term 'satisfied'", "Count reviews mentioning a term"),
    ("top-1 best-selling product in 2022", "Top best-selling product"),
    ("top-5 best-selling products in 2023", "Top-5 best-selling products"),
    ("top-1 best-selling brand", "Top best-selling brand"),
    ("List the top 3 search terms", "Top search terms report"),
    ("most frequently among the top search terms", "Most frequent brand in search terms"),
    ("customer name of the most recent cancelled order", "Most recent cancelled order"),
    ("order ID of the newest pending order", "Newest pending order ID"),
    ("billing name of the oldest complete order", "Oldest complete order"),
    ("purchase date and order id of the most recent pending", "Most recent pending order"),
    ("customer name and email with a given phone", "Customer lookup by phone"),
    ("total count of Pending reviews", "Pending reviews count"),
]

MIN_WEB_SCREENS = 3  # skip runs too short to read as a simulator

def find_web(progs, frag):
    fl = frag.lower()
    cands = [d for d in progs.values()
             if d['metadata'].get('application_context', '').startswith('http')
             and fl in d['metadata'].get('task_description', '').lower()
             and d['metadata'].get('source_trace_id')
             and os.path.isdir(os.path.join(ROOT, 'traces', d['metadata']['source_trace_id']))]
    def nimg(d):
        tid = d['metadata']['source_trace_id']
        return len([f for f in os.listdir(os.path.join(ROOT, 'traces', tid)) if f.endswith('.png')])
    cands = [d for d in cands if nimg(d) >= MIN_WEB_SCREENS]
    if not cands:
        return None
    # prefer richest program with the most screenshots
    return max(cands, key=lambda d: (len(d['states']), nimg(d)))

# ---------------------------------------------------------------- desktop (corpus)
def load_corpus_desktop():
    s = open(os.path.join(SITE, 'src/data/corpus.js')).read()
    arr = json.loads(s[s.index('['):s.rindex(']') + 1])
    return [p for p in arr if p['platform'] == 'desktop']

DESKTOP_NAMES = {
    'Could you tone down the brightness': 'Tone down photo brightness',
    'enhancing the color vibrancy': 'Boost photo color vibrancy',
    'make Bing the main search engine': 'Set Bing as search engine',
    'quick way back to this site': 'Bookmark the current site',
    'clean up my computer by getting rid': 'Clear browsing history',
    'Names with duplicates': 'Flag duplicate names in Calc',
    'Compute the sum of': 'Sum two columns in Calc',
    'line spacing of first two paragraph': 'Double line-spacing in Writer',
    'remove the account': 'Remove a Thunderbird account',
    'wrongly deleted': 'Restore a file from Trash',
    'conda install datasets': 'Fix a conda install error',
    'file named "secret.docx"': 'Find a file in the terminal',
    'LibreOffice Writer seems to have frozen': 'Kill a frozen app',
    'start VS Code in folder': 'Open a folder in VS Code',
    'change all the places in this document': 'Find-and-replace in a doc',
    'open the "project" in the': 'Open a project in VS Code',
    'line length for code': 'Set the editor ruler in VS Code',
}

def desktop_name(task):
    for frag, name in DESKTOP_NAMES.items():
        if frag.lower() in task.lower():
            return name
    return task[:40]

# ---------------------------------------------------------------- main
def main():
    progs = load_all()
    print('loaded', len(progs), 'programs')

    android = []
    for tid, name, prefix in TRAJ:
        d = find_android(progs, prefix)
        imgs = list_traj_imgs(tid)
        if not d:
            print('  android MISS:', name)
            continue
        p = normalize_android(d)
        p.update({'id': tid, 'name': name, 'platform': 'android', 'screens': imgs})
        android.append(p)
        print(f'  android OK  {name:22} states={len(p["states"])} imgs={len(imgs)}')

    web = []
    used = set()
    for frag, name in WEB_PICKS:
        d = find_web(progs, frag)
        if not d:
            print('  web MISS:', name); continue
        pid = d['metadata']['program_id']
        if pid in used:
            print('  web dup skip:', name); continue
        used.add(pid)
        p = normalize_web(d)
        screens = copy_web_screens(pid, p['trace'])
        p.update({'id': pid, 'name': name, 'platform': 'web', 'screens': screens})
        p.pop('trace', None)
        web.append(p)
        print(f'  web OK      {name:34} states={len(p["states"])} imgs={len(screens)}')

    desktop = []
    for p in load_corpus_desktop():
        q = {'id': re.sub(r'[^a-z0-9]+', '-', p['task'].lower())[:32].strip('-'),
             'name': desktop_name(p['task']), 'task': p['task'], 'app': p['app'],
             'platform': 'desktop', 'params': p.get('params', []),
             'states': p['states'], 'transitions': p['transitions'], 'screens': []}
        desktop.append(q)
    print(f'  desktop: {len(desktop)} programs')

    out = {'android': android, 'desktop': desktop, 'web': web}
    header = (
        "// Real compiled programs, shown as runtime-execution simulators.\n"
        "// Generated by scripts/build_programs_data.py from the chroma program stores\n"
        "// (rag_db*) and corpus.js. Each program is the actual state machine PreAct\n"
        "// compiled from a successful benchmark run: states carry the verification\n"
        "// predicate checked at replay time, transitions carry the action taken.\n"
        "// Android + Web programs include the real screenshots from that run;\n"
        "// Desktop (OSWorld) programs are program-only (no screenshots were recorded).\n\n"
        "export const PROGRAMS = "
    )
    path = os.path.join(SITE, 'src/data/programs.js')
    with open(path, 'w') as f:
        f.write(header + json.dumps(out, indent=2) + "\n")
    print('wrote', path)
    print(f'TOT:  android={len(android)} desktop={len(desktop)} web={len(web)}')

if __name__ == '__main__':
    main()
