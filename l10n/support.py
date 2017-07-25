# -*- coding: utf-8 -*-

from gettext import translation
import babel.support
import pkg_resources

LOCALES = ['en_US', 'ru_RU']


class L10nSupport(object):
    '''
    Localization support.

    '''

    def __init__(self, lang):
        self.locale = self.to_locale(lang)
        locale_dir = pkg_resources.resource_filename('l10n', 'locales')  # @UndefinedVariable
        self.translations = babel.support.Translations.load(dirname=locale_dir,
                                                            locales=[self.locale])
        t = translation('messages', localedir=locale_dir, languages=[self.locale])
        try:
            t.install(unicode=True)  # Python 2
        except:  # @IgnorePep8
            t.install()  # Python 3

    def get_locales(self):
        return LOCALES

    def get_locale(self):
        return self.locale

    def to_locale(self, lang):
        for l in self.get_locales():
            if l.startswith(lang):
                return l
        return None

    def get_translations(self):
        return self.translations
