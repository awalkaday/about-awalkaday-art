from pathlib import Path

chapters = [
    ("one-step-forward",           "one-step-forward.md"),
    ("artist-statement",           "artist-statement.md"),
    ("reading-guide",              "reading-guide.md"),
    ("introduction-to-the-photo-series", "introduction-to-the-photo-series.md"),
    ("beyond-pixels",              "beyond-pixels-a-stroll-into-nature.md"),
    ("mobile-studio",              "mobile-studio-and-digital-toolkit/README.md"),
    ("mobile-studio-on-the-go",    "mobile-studio-and-digital-toolkit/on-the-go-photography.md"),
    ("mobile-studio-cameras",      "mobile-studio-and-digital-toolkit/cameras-and-photo-editing.md"),
    ("mobile-studio-gaming",       "mobile-studio-and-digital-toolkit/gaming-laptop.md"),
    ("chronicle",                  "chronicle-of-milestones-navigation/README.md"),
    ("chronicle-parallel",         "chronicle-of-milestones-navigation/parallel-pathways.md"),
    ("chronicle-internet",         "chronicle-of-milestones-navigation/internet-footprints.md"),
    ("chronicle-blockchain",       "chronicle-of-milestones-navigation/blockchain-records.md"),
    ("evolution",                  "evolution-of-a-trek-on-platforms/README.md"),
    ("evolution-instagram",        "evolution-of-a-trek-on-platforms/instagram.md"),
    ("evolution-twitter",          "evolution-of-a-trek-on-platforms/x-twitter.md"),
    ("evolution-github",           "evolution-of-a-trek-on-platforms/github.md"),
    ("evolution-ethereum",         "evolution-of-a-trek-on-platforms/ethereum.md"),
    ("evolution-web",              "evolution-of-a-trek-on-platforms/web-gallery.md"),
    ("artists-proofs",             "artists-proofs-and-ethos/README.md"),
    ("artists-proofs-commits",     "artists-proofs-and-ethos/public-git-commits.md"),
    ("artists-proofs-oss",         "artists-proofs-and-ethos/open-source-software.md"),
    ("artists-proofs-git",         "artists-proofs-and-ethos/git-usage-history.md"),
    ("artist-profiling",           "artist-profiling/README.md"),
    ("artist-profiling-inception", "artist-profiling/project-inception.md"),
    ("artist-profiling-human",     "artist-profiling/human-identity.md"),
    ("artist-profiling-training",  "artist-profiling/training-ground.md"),
    ("contact",                    "contact.md"),
    ("imprint",                    "imprint.md"),
    ("catalogue",                  "catalogue.md"),
    ("appendix",                   "appendix.md"),
    ("postscript",                 "postscript.md"),
]

missing = []
for slug, path in chapters:
    if not Path(path).exists():
        missing.append(path)

if missing:
    print(f"MISSING {len(missing)} files:")
    for m in missing:
        print(f"  {m}")
else:
    print(f"All {len(chapters)} chapter files present — ready to wire impression/index.md")
