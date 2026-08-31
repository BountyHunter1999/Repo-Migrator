# Repo-Migrator
Migrate Repo from Source Control to Another

## Move Repo

Move repo branches, tags, and LFS

1. `git clone --mirror git@bitbucket.org:<org>/<repo>.git`
2. `git lfs fetch --all` Fetch LFS objects
3. `git remote add github git@github.com:<org>/<repo>.git`
4. `git push --mirror github`

### To Sync Changes

1. `git remote update`
2. `git push --mirror github`

## PR Template

1. Create `.github/PULL_REQUEST_TEMPLATE/pull_request_template.md`; remember, this should be present in the default branch
    - For another option, follow [this](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/creating-a-pull-request-template-for-your-repository)
