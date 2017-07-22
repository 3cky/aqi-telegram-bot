#!/bin/sh
locales="en_US ru_RU"
locales_dir="l10n/locales"
pybabel extract -F $locales_dir/babel.cfg -o $locales_dir/messages.pot ./
for locale in $locales; do
    pybabel update -l $locale -d $locales_dir -i $locales_dir/messages.pot
done
