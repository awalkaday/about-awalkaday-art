from pathlib import Path

restorations = {
    'chronicle-of-milestones-navigation/README.md':
        'A timeline lining up bits and pieces of the scaffolding and the milestones marking progressive moves of data flows on a cyber terrain',
    'artists-proofs-and-ethos/README.md':
        'Reframing version control philosophy as artistic methodology through transparent iteration, public refinement, and trails of GIT commits',
    'evolution-of-a-trek-on-platforms/README.md':
        'Five territories map out nomadism from one computing platform to another in search of visibility, transparency, presentation, discourse, or permanence',
    'artist-profiling/README.md':
        'A portrait of a Burundian assembled from fragments of darkened memories: Beijing to Brussels, war filming to refuge seeking, engineer-in-training to undocumented',
}

for filepath, description in restorations.items():
    f = Path(filepath)
    text = f.read_text(encoding='utf-8').replace('\r\n', '\n')
    if 'description:' in text:
        print(f'already has description: {filepath}')
        continue
    text = text.replace('---\n', f'---\ndescription: "{description}"\n', 1)
    f.write_text(text, encoding='utf-8')
    print(f'restored: {filepath}')
