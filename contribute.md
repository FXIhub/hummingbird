# How to contribute

## 1. Create an issue on Github
Go to the issue tracker ![](https://github.com/FXIhub/hummingbird/issues) and create an issue/task/enhancement you would like to work on.
Don't forget to label it appropriately. If the issue you want to work on exists already, you can skip this step.
In any case, please assign yourself to the issue such that others can see it.

## 2. Create a new branch
Go to your clone of the **Hummingbird** repository and create a new branch
```
git checkout -b issue/XX/description

```
with the issue number and a short description in the branch name.

## 3. Work and commit to your local branch
Just commit and push your changes as usual
```
git push -u origin issue/XX/description
```
Make sure you have locally run the tests
```
py.test
```
before you continue to the next step.

## 4. Create a new pull request
You can create a pull request from your branch on the Github page (![](https://github.com/FXIhub/hummingbird/pull/new/master)) or
from the command line (if you have *hub* installed, e.g. by using `brew install hub`):
```
hub pull-request -i XX 
```
Now your changes can be reviewed.

## (5. Review changes and merge the pull request)
If you have the priviliges you can handle the pull-request using the Github page: ![](https://github.com/FXIhub/hummingbird/pulls). Make sure that 
the issue branch is deleted again after the pull request has been merged.

