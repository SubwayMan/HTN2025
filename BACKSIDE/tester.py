from fetcher import *

testrepo = "patrick-gu/toot"
d = DataFetcher()
print(d.fetch_github_repository(testrepo, "../workspace"))
