# -*- coding: utf-8 -*-
# Copyright (C) 2008 Jan Svec and Filip Jurcicek
# 
# YOU USE THIS TOOL ON YOUR OWN RISK!
# 
# email: info@gmail-backup.com
# 
# 
# Disclaimer of Warranty
# ----------------------
# 
# Unless required by applicable law or agreed to in writing, licensor provides
# this tool (and each contributor provides its contributions) on an "AS IS"
# BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied, including, without limitation, any warranties or conditions of
# TITLE, NON-INFRINGEMENT, MERCHANTABILITY, or FITNESS FOR A PARTICULAR
# PURPOSE. You are solely responsible for determining the appropriateness of
# using this work and assume any risks associated with your exercise of
# permissions under this license. 

"""Framework pro parametrizaci skriptů

Úvod
====

Rychlé prototypování v jazyce Python umožňuje vyvinutí samotného skriptu nebo
aplikace během několika hodin. Má-li však skript (aplikace) být široce
použitelnou, je třeba zpracovat kvalitní uživatelské rozhraní. Toto může být
zpracováno jednak pomocí příkazové řádky, konfiguračních souborů nebo
grafického uživatelského rozhraní.

Každý z těchto přístupů umožňuje (resp. vyžaduje) zadávání parametrů skriptu
pomocí řetězců. Zpracování a konverze těchto řetězců je úkolem aplikace.
Poněvadž jde o část aplikační logiky, jež se neustále opakuje, je možné ji
vyčlenit do samostatného frameworku.

Požadavky kladené na tento framework jsou především následující:

    - Použití řetězců jako vstupních parametrů.
    - Možnost specifikace požadavků na parametry (vícenásobný, vyžadovaný,
      návratový ...).
    - Práce s více zdroji parametrů zároveň (příkazová řádka, konfigurační
      soubory, proměnné prostředí, GUI).
    - Možnost spojit parametry z více zdrojů v jeden parametr.

Návrh
=====

Reprezentací parametrizovatelného skriptu ve frameworku `svc.scripting` je
instance třídy `ParametrizedObject`. Volby předané skriptu jsou funkčnímu
objektu předány jako hodnoty funkčních argumentů. To umožňuje používat kódovací
styl, kdy je nejprve napsána určitá funkce sloužící jako hlavní funkce skriptu,
odladěna pomocí testovacích funkcí a následně "zparametrizována" pomocí
frameworku ``svc.scripting``.

.. image:: ../uml1.png

Instance třídy ``OptionManager`` zodpovídá za správu všech parametrů (voleb,
options) funkčního objektu.  Umožňuje získávání jmen voleb, jejich konverzních
funkcí a požadavků na tyto volby (specifiers, např. `Multiple` - vícenásobná
volba nebo `Required` - požadovaná volba). Obsahuje též metody pro kontrolování
(`OptionManager.validate`) a konverzi (`OptionStack.popObjects`) seznamu voleb
ve tvaru řetězců do tvaru objektů.

Při volání parametrizovaného objektu jsou provedeny následující operace
zůčastněných objektů:

.. image:: ../uml2.png

V současné době je ve frameworku implementována jediná třída s rozhraním
``ExternalAdapter`` - třída `Script`. Pro napsání vlastního skriptu je třeba
odvodit potomka této třídy a v něm předefinovat následující metody a atributy:

    - ``main`` - hlavní metoda skriptu, která je po provedení konstruktoru
      převedena na instanci třídy `ParametrizedObject`.
    - ``options`` - atribut typu ``dict`` specifikující popis jednotlivých voleb
      skriptu. Více viz třída `OptionManager`.
    - ``shortOpts``, ``posOpts`` - atributy popisující chování extraktoru
      `extractors.CmdlineExtractor` sloužícího pro získávání voleb z příkazové řádky.
    - ``envPrefix`` - atribut sloužící pro vytvoření extraktoru
      `extractors.EnvironExtractor`.
    - ``pyFiles``, ``pyFilesGlobals`` - atributy pro konstruktor extraktoru
      `extractors.PyFileExtractor`.
    - ``writeReturnValue`` - metoda sloužící pro uložení návratové hodnoty
      skriptu.

Pokud odděděná třída nepředefinuje atributy specifikující chování extraktorů,
použijí se výchozí hodnoty. Konstruktor třídy ``Script`` vytvoří na základě
metody `Script.main` a atributu `Script.options` instanci třídy
``ParametrizedObject``, přičemž nastaví adapter této instance (pomocí
`ParametrizedObject.setAdapter`) na instanci třídy ``Script``.

.. image:: ../uml3.png

Třída ``Script`` používá pro získání hodnota jednotlivých voleb z vnějšího
prostředí tzv. extraktory - třídy implementující rozhraní `Extractor`.
Extraktory jsou vytvářeny metodou `Script.createExtractors`. 

Rozhraní ``Extractor`` umožňuje nastavení a získání zdroje extraktoru (metody
`Extractor.getSource` a `Extractor.setSource`), získání jména zdroje extraktoru
(`Extractor.getSourceName`), získání seznamu voleb pomocí extraktoru
(`Extractor.extract`). Extraktory rovněž obdrží odkaz na instanci třídy
``OptionManager`` (`Extractor.setManager`). V případě, že objekt ``Script``
požaduje použití implicitního zdroje, použije ``Extractor.setSource(None)``.

Jméno zdroje extraktoru slouží pro jejich centralizovanou správu. Tu zajišťují
metody `Script.getSources` a `Script.setSources`. Centrální nastavení zdrojů
používá asociativní pole, přičemž jeho klíče odpovídají jménům zdrojů
extraktorů podle `Extractor.getSourceName` a hodnoty jsou zdroje následně
nastavené metodou `Extractor.setSource`.

Posloupnost operací vykonaných při vytvoření nové instance třídy `Script`:

.. image:: ../uml4.png

Při volání metody `Script.run` dojde k nastavení zdrojů pomocí
`Script.setSources` a následně k zavolání instance třídy `ParametrizedObject`.
Následuje obvyklý scénář spolupráce instance ``ParametrizedObject`` s rozhraním
``ExternalAdapter``:

.. image:: ../uml5.png

Seznamy voleb ve formě řetězců navrácených metodami `Extractor.extract` jsou
zřetězeny do jediného seznamu a předány metodě
`OptionStack.popObjects`. Je-li této metodě předán seznam, v němž jsou
dvě volby specifikovány v různých zdrojích, pak volba definovaná později
přepíše původní hodnotu. Je-li však použit specifikátor `JoinSources`, jsou
tyto hodnoty řazeny za sebou do jediného seznamu. Metoda
`OptionManager.validate` kontroluje chyby při zadávání voleb, například zadání
jednoduché volby vícekrát v jednom zdroji, vynechání povinné volby, zadání
neznámé volby apod.

Příklad
=======

Mějme následující funkci pro kopírování souborů::

    def cp(source, destination, verbose=False):
        if len(source) == 0:
            raise ValueError("You must specify source files")
        if os.path.isdir(destination):
            for fn in source:
                fn_file = os.path.basename(fn)
                if verbose:
                    print fn
                fr = file(fn)
                fw = file(os.path.join(destination, fn_file), 'w')
                try:
                    fw.write(fr.read())
                finally:
                    fr.close()
                    fw.close()
        else:
            if len(source) > 1:
                raise ValueError("Destination must be directory")
            if verbose:
                print fn
            fr = file(source[0])
            fw = file(destination, 'w')
            try:
                fw.write(fr.read())
            finally:
                fr.close()
                fw.close()

Nyní tuto funkci použijeme pro vytvoření modulu - skriptu, jež bude obdobou
UNIXového příkazu ``cp`` (následující kód uložme do souboru ``cp.py``)::

    #!/usr/bin/env python2.4
    import os
    from svc.scripting import *

    def cp(source, destination, verbose=False):
        ... # See above

    class CP(Script):
        debug = False
        debugMain = False

        main = staticmethod(cp)
        options = {
            'source': (Required, Multiple, String),
            'destination': (Required, String),
            'verbose': Flag,
        }

        shortOpts = {'v': 'verbose'}
        posOpts = ['source', Ellipsis, 'destination']

    if __name__ == '__main__':
        script = CP()
        script.run()

Vytvořili jsme obálkovou třídu ``CP`` odděděnou od třídy `Script`. Dále jsme
vypnuli její ladicí možnosti, tj. při výjimkách se bude vypisovat pouze
jednořádkové hlášení o chybě. Jako hlavní metodu ``main`` jsme přiřazením
určili funkci ``cp``. Pro použití jako metoda musí být funkce ``cp`` převedena
na statickou metodu.

Dále jsme určili typ jednotlivých voleb. Volba ``source`` reprezentující jména
zdrojových souborů je povinná a může být specifikována vícekrát. Její typ je
řetězec (``String``). Obdobně jméno cílového souboru, popř. adresáře, musí být
určeno a je řetězcového typu. Nakonec volba ``verbose`` zapínající tisk
ladicích informací je typu příznak (``Flag``).

Následují dva atributy určující chování třídy `extractors.CmdlineExtractor`.
Prvním je slovník ``shortOpts``, jde o výčet krátkých argumentů příkazového
řádku.  V našem případě tedy můžeme na příkazovém řádku zapsat ``-v`` namísto
``--verbose`` se stejným efektem. Druhý atribut ``posOpts`` je seznam mapující
jména pozičních argumentů na jména voleb. Hodnota `Ellipsis` v tomto případě
znamená *maximální množství voleb* a může být použita pouze jednou. Volba
``source`` tedy z příkazové řádky obdrží poziční argumenty (nikoli krátké nebo
dlouhé argumenty) příkazové řádky 1 až (N-1), zatímco volba ``destination``
obdrží poslední N-tý argument.

Poslední tři řádky zajistí vytvoření a spuštění instance třídy ``CP``, pokud je
modul spuštěn jako hlavní modul jazyka Python. Uložíme-li zdrojový kód do
souboru ``cp.py``, můžeme ho používat následujícím způsobem ($ značí výzvu
příkazového řádku)::
    
    $ ./cp.py
    Script CP: Option 'destination' is not specified
    $ ./cp.py xyz.txt
    Script CP: Option 'source' is not specified
    $ ./cp.py abc.txt xyz.txt
    $ ./cp.py -v abc.txt xyz.txt
    abc.txt
    $ ./cp.py --verbose abc.txt opq.txt xyz.txt dir
    abc.txt
    opq.txt
    xyz.txt
    $ ./cp.py dir xyz.txt
    Script CP: IOError: [Errno 21] Is a directory

:Variables:
    - `Required` - specifikátor *povinné* volby
    - `Multiple` - specifikátor *vícenásobné* volby
    - `JoinSources` - specifikátor *vícenásobné* volby, přičemž je možné
      spojovat volby definované ve více zdrojích
    - `EnvVar` - volba s tímto specifikátorem může být specifikována proměnnou
      prostředí
    - `FullParam` - je-li použito jako specifikátor, pak jméno volby je určeno
      jeho plnou cestou s tečkami '.' nahrazenými podtržítkem '_', jinak je
      jako jméno volby použit poslední element cesty (tj. jméno za poslední
      tečkou).
    - `Prior` - konverze voleb s tímto specifikátorem je provedena před
      konverzí ostatních
"""
import sys
import os
import logging
import inspect

from svc.egg import PythonEgg
from svc.utils import sym, issequence, isstr, seqIntoDict
from svc.scripting.conversions import *
from svc.scripting.help import HelpManager

__docformat__ = 'restructuredtext cs'

Required = sym('Required')
Multiple = sym('Multiple')
JoinSources = sym('JoinSources')
FullParam = sym('FullParam')
EnvVar = sym('EnvVar')
Prior = sym('Prior')

# TODO: Other specifiers
# GlobOption = sym('GlobOption')
# FlatList = sym('FlatList')

OptionAlias = sym('OptionAlias')

class ParametrizedObject(PythonEgg):
    """Třída reprezentující parametrizovaný objekt

    :Ivariables:
        - `_state` - odkaz na objekt `OptionStack` obsahující stav konverze
          objektů. Existuje po dobu od zavolání `createState` do zavolání
          `destroyState`. Po tuto dobu k němu lze přistupovat pomocí metody
          `getState`.
    """
    def createState(self):
        raise TypeError("Abstract method ParametrizedObject.createState()")

    def getState(self):
        return self._state

    def setState(self, state):
        self._state = state

    def destroyState(self):
        del self._state

    def premain(self):
        self.state.enableAll()
        self.state.disable(self.state.manager.paramsChildren('__premain__'))
        return False

    def main(self):
        raise TypeError("Abstract method ParametrizedObject.main()")
    
    def run(self):
        """Zavolá parametrizovaný objekt

        Nejprve jsou pomocí `ExternalAdapter.extractOptions` získány volby ve
        formě řetězců, následně jsou metodou `OptionStack.popObjects`
        převedeny na objekty. Následně dojde k rozdělení na *přímé* a
        *návratové* volby. Poté je zavolána hlavní funkce s přímými volbami a
        nakonec je její návratová hodnota uložena pomocí
        `ExternalAdapter.writeReturnValue`.

        Při vzniklých výjimkách jsou zavolány příslušné handlery chyb.
        """

        self.createState()
        self.state.disableAll()
        self.state.enable(self.manager.paramsChildren('__premain__'))

        retval = True
        while retval:
            try:
                objects = self.state.popObjects()
            except OptionError:
                self._validationError(sys.exc_info()[1])
            except:
                self._conversionError(sys.exc_info()[1])

            premain_opts = objects.get('__premain__', {})
            try:
                retval = self.premain(**premain_opts)
            except SystemExit:
                raise
            except:
                self._mainError(sys.exc_info()[1])


        try:
            objects = self.state.getObjects()
        except OptionError:
            self._validationError(sys.exc_info()[1])
        except SystemExit:
            raise
        except:
            self._conversionError(sys.exc_info()[1])

        try:
            retval = self.main(**objects)
        except:
            self._mainError(sys.exc_info()[1])

        self.destroyState()

        return retval

    def _conversionError(self, e):
        raise

    def _validationError(self, e):
        raise
    
    def _mainError(self, e):
        raise

class OptionError(Exception):
    def __init__(self, msg, option=''):
        Exception.__init__(self, msg, option)
        self.option = option
        self.msg = msg

    def __str__(self):
        return self.msg

class OptionManager(PythonEgg):
    """Třída pro správu, kontrolu a konverzi voleb

    Vstupním údajem pro vytvoření instance je tzv. *specifikace voleb*. Jde o
    slovník, jehož klíče jsou názvy voleb a hodnoty určují jejich konkrétní
    vlastnosti. Hodnoty jsou tuple obsahující *specifikátory*, *konverzní
    funkci* a její *dodatečné argumenty*.

    Příklad:
    ========

    ::

        specification = {
            'option1' : Integer,
            'option2' : (Required, Integer),
            'option3' : (Required, ListOf, Integer),
        }

    V uvedeném příkladě je volba ``option1`` číslo. Její konverzní funkce je
    funkce `Integer`. Pokud volbu určuje pouze konverzní funkce, lze ji uvést
    jako samostatnou hodnotu a ne jak tuple.

    Volba ``option2`` je opět celé číslo. Podle specifikátoru před konverzní
    funkci jde však o volby povinnou (`Required`).

    Konečně volba ``option3`` je seznam celých čísel. Konverzní funkce `ListOf`
    bude volána ve tvaru::

        ListOf(option_value, Integer)

    kde ``option_value`` je hodnota volby typu řetězec. Konverzní funkce
    `ListOf` rozdělí řetězec podle znaků čárka a na výslednou posloupnost
    řetězců aplikuje konverzní funkci `Integer`, jež jí byla předána jakou
    druhý argument.

    Získání jednotlivých položek ze specifikace volby probíhá následovně:

        1. Specifikace volby musí obsahovat alespoň jeden objekt, jež je
           funkčním objektem - *konverzní funkcí* (viz metoda `conversion`).
        2. Všechny objekty před konverzní funkcí jsou *specifikátory* (viz
           `Required`, `Multiple` atd., též metoda `specifiers`).
        3. Všechny objekty za konverzní funkcí jsou *dodatečné argumenty*
           konverzní funkce a jsou jí předány za hodnotou konvertovaného
           řetězce (viz metoda `conversion`).

    :Ivariables:
        - `_specification` - specifikace voleb
        - `_rawspec` - undocumented
    """

    def __init__(self, specification, docs={}):
        self._aliases = set()
        self._optionAliases = {}
        self.specification = specification
        self.helpForOptions = docs
    
    def getSpecification(self):
        """Vrátí aktuální specifikaci voleb
        """
        return self._specification

    def setSpecification(self, specification):
        """Nastaví novou specifikaci voleb
        """
        self.validateSpecification(specification)
        self._specification = specification
        rawspec = self._rawspec = {}
        param2option = self._paramToOptionMap = {}
        option2param = self._optionToParamMap = {}

        aliases = set()

        for key, value in specification.iteritems():
            if value == OptionAlias:
                aliases.add(key)
                continue

            if not issequence(value):
                value = [value]
            specifiers = []
            conversion = None
            args = []
            for i in value:
                if callable(i) and not conversion:
                    conversion = i
                elif not conversion:
                    specifiers.append(i)
                else:
                    args.append(i)
            specifiers = frozenset(specifiers)

            if FullParam not in specifiers:
                # Get option name from parameter name
                new_key = self._splitOptionName(key)
            else:
                # Convert dotted parameter into underscored parameter
                new_key = key.replace('.', '_')

            if new_key in option2param:
                raise ValueError("%r and %r both maps to %r" \
                                 % (key, option2param[new_key], new_key))
            option2param[new_key] = key
            param2option[key] = new_key
            rawspec[key] = (specifiers, conversion, args)

        self.setAliases(aliases)
    
    def getAliases(self):
        return self._aliases

    def setAliases(self, aliases):
        del self.aliases
        self._aliases = set(aliases)
        self._optionAliases = {}
        for param in self._aliases:
            option = self._splitOptionName(param)
            self._paramToOptionMap[param] = option
            ref_param = self.optionToParam(option)
            self._rawspec[param] = self._rawspec[ref_param]
            if option not in self._optionAliases:
                self._optionAliases[option] = set([ref_param])
            self._optionAliases[option].add(param)

    def delAliases(self):
        # FIXME: Remove
        for param in self._aliases:
            del self._paramToOptionMap[param]
            del self._rawspec[param]
        self._aliases.clear()
        self._optionAliases.clear()

    def getHelpForOptions(self):
        return self._helpForOptions

    def setHelpForOptions(self, help):
        unknown = set(help.keys()) - self.options()
        if unknown:
            raise ValueError("Unknown option: %r" % unknown.pop())
        self._helpForOptions = help

    def options(self):
        """Vrátí seznam jmen všech voleb
        """
        return set(self.paramToOption(k) for k in self.params())

    def optionsWithSpecifier(self, specifier):
        """Vrátí seznam jmen všech voleb SE specifikátorem `specifier`
        """
        return set(self.paramToOption(k) for k in self.paramsWithSpecifier(specifier))

    def optionsWithoutSpecifier(self, specifier):
        """Vrátí seznam jmen všech voleb BEZ specifikátoru `specifier`
        """
        return set(self.paramToOption(k) for k in self.paramsWithoutSpecifier(specifier))

    def params(self):
        """Vrátí seznam jmen všech parametrů
        """
        return set(self._rawspec)

    def paramsWithSpecifier(self, specifier):
        """Vrátí seznam jmen všech parametrů SE specifikátorem `specifier`
        """
        return set(key for (key, (s, c, a)) in self._rawspec.iteritems()
                      if specifier in s)

    def paramsWithoutSpecifier(self, specifier):
        """Vrátí seznam jmen všech parametrů BEZ specifikátoru `specifier`
        """
        return set(key for (key, (s, c, a)) in self._rawspec.iteritems()
                      if specifier not in s)

    def paramsAbove(self, level):
        """Vrátí množinu jmen parametrů na úrovni nejvýše `level`
        """
        return set(p for p in self.params() if len(self._splitParam(p)) <= level)

    def paramsBelow(self, level):
        """Vrátí množinu jmen parametrů na úrovni pod `level`
        """
        return set(p for p in self.params() if len(self._splitParam(p)) > level)

    def paramsChildren(self, param):
        """Vrátí množinu parametrů, jež jsou dětmi parametru `param`
        """
        param_t = self._splitParam(param)
        m = len(param_t)
        return set(p for p in self.params() if self._splitParam(p)[:m] == param_t)

    def specifiers(self, paramName):
        """Vrátí všechny specifkátory parametru `paramName`
        """
        return self._rawspec[paramName][0]
    
    def conversion(self, paramName):
        """Vrátí dvojici (konverzní_funkce, dodatečné_argumenty) pro parametr `paramName`
        """
        return self._rawspec[paramName][1:]

    def validateSpecification(self, specification):
        """Provede kontrolu specifikace (nepoužito)
        """

    def paramToOption(self, param):
        try:
            return self._paramToOptionMap[param]
        except KeyError:
            raise OptionError("Unknown param %r" % param, param)

    def optionToParam(self, option):
        try:
            return self._optionToParamMap[option]
        except KeyError:
            raise OptionError("Unknown option %r" % option, option)

    def optionToAliases(self, option):
        aliases = self._optionAliases.get(option, None)
        if aliases is not None:
            return aliases
        else:
            return set([self.optionToParam(option)])

    def _splitParam(self, param):
        return param.split('.')

    def _splitOptionName(self, param):
        return self._splitParam(param)[-1]

class OptionStack(PythonEgg, list):
    """Třída pro uchovávání aktuální stavu OptionManageru
    """
    def __init__(self, manager):
        self._enabledParams = set()
        self.setManager(manager)
        super(OptionStack, self).__init__()

    def getManager(self):
        return self._manager
    
    def setManager(self, m):
        self._manager = m
        self.clear()

    def clear(self):
        """Znovupovolí všechny parametry a vymaže stav
        """
        self.enableAll()
        del self[:]

    def _checkParams(self, params):
        """Provede kontrolu `params` a vrátí ho jako množinu

        Kontroluje neexistující parametry.
        """
        params = set(params)
        bad_params = params - self.manager.params()
        if bad_params:
            bad_param = bad_params.pop()
            raise OptionError("Unknown parameter in set: %r" % bad_param, bad_param)
        return params

    def enable(self, params):
        """Povolí pouze parametry `params`
        """
        self._enabledParams |= self._checkParams(params)

    def enableAll(self):
        """Povolí všechny parametry
        """
        self._enabledParams = self.manager.params()

    def enableExcept(self, params):
        """Povolí všechny parametry kromě `params`
        """
        self._enabledParams = self.manager.params() - self._checkParams(params)

    def disable(self, params):
        """Zakáže pouze parametry `params`
        """
        self._enabledParams -= self._checkParams(params)

    def disableAll(self):
        """Zakáže všechny parametry
        """
        self._enabledParams.clear()

    def disableExcept(self, params):
        """Zakáže všechny parametry kromě `params`
        """
        self._enabledParams = self._checkParams(params)

    def getEnabled(self):
        """Vrátí množinu všech povolených parametrů
        """
        return set(self._enabledParams)

    def getDisabled(self):
        """Vrátí množinu všech zakázaných parametrů
        """
        return self.manager.params() - self._enabledParams

    def popObjects(self):
        return self.getObjects(_pop=True)

    def getObjects(self, _pop=False):
        """Převede zásobník voleb na slovník 

        Ze seznamu voleb ve formě řetězců vytvoří slovník, jehož klíče jsou
        rovny jménům voleb a hodnoty objektům vzniklým po konverzi řetězců.

        Seznam voleb je tvořen uspořádanými čteřicemi ve tvaru::

            (name, value, source_name, description)

        kde ``name`` je jméno volby, ``value`` její řetězcová hodnota,
        ``source_name`` je jméno zdroje, ze kterého pochází a ``description``
        je libovolný textový popis volby, který se použije při výpisu chyby.
            
        Je možné, aby ``value`` byl i libovolný objekt, pak se nebude provádět
        konverzní funkce a použije se rovnou hodnota tohoto objektu.

        Před vlastní konverzí je zavolána metoda `validate` pro kontrolu
        správnosti seznamu voleb.
        """
        self.validate()
        objects = _OptionTree(self.manager)
        not_processed = []
        yet_processed = set()

        def isntPrior(item):
            return Prior not in self.manager.specifiers(self.manager.optionToParam(item[0]))

        for item in sorted(self, key = isntPrior):
            opt_name, opt_val, source, desc = item
            # Create param name from the short option name
            par_name = self.manager.optionToParam(opt_name)
            targets = self.manager.optionToAliases(opt_name)

            if not (targets & self.enabled):
                # If parameter is disabled, parameter value will be stored for
                # future processing
                not_processed.append(item)
                # Skip disabled parameters
                continue

            opt_val = self.convertParameter(par_name, opt_val)

            for par_name in targets & self.enabled:
                objects.storeValue(par_name, opt_val, source)

                # Store parameter into an already processed set
                yet_processed.add(par_name)

        if _pop:
            # Store not processed items in OptionStack for future processing
            self[:] = not_processed
            # Disable already processed parameters
            self.disable(yet_processed)

        return objects.nested()

    def convertParameter(self, par_name, str_value):
        if isstr(str_value):
            # If opt_val is string, call conversion function
            conv_func, conv_args = self.manager.conversion(par_name)
            try:
                return conv_func(str_value, *conv_args)
            except:
                e = sys.exc_info()[1]
                e.optionName = par_name
                raise
        else:
            return str_value

    def validate(self):
        """Zkontroluje zásobník voleb 

        Hledá tři typy chyb:
            
            1. Volby bez specifikace (chybně zapsané volby, překlepy)
            2. Vícekrát určené jednoduché volby (vícenásobné použití parametru
               na příkazové řádce apod.)
            3. Chybějící povinné volby (tj. se specifikátorem `Required`)

        :Raises ValueError:
            Při porušení libovolného pravidla 1. - 3.
        """
        opt_counts = dict((key, 0) for key in self.manager.params())
        par_specs = dict((key, self.manager.specifiers(key)) for key in self.manager.params())
        opt_lastsource = dict((key, None) for key in self.manager.options())
        for opt_name, par_str_val, source_name, desc in self:
            # If option has no enabled alias, skip this option
            aliases = self.manager.optionToAliases(opt_name)
            if not aliases & self.enabled:
                continue

            par_name = self.manager.optionToParam(opt_name)

            if opt_lastsource[opt_name] != source_name:
                opt_counts[opt_name] = 0
            opt_counts[opt_name] += 1
            opt_count = opt_counts[opt_name]
            par_spec = par_specs[par_name]
            if opt_count > 1 and not (Multiple in par_spec or JoinSources in par_spec):
                raise OptionError("Option %r specified multiple times (source: %s, %s)" \
                                 % (opt_name, source_name, desc), opt_name)

            opt_lastsource[opt_name] = source_name

        for par_name in self.manager.paramsWithSpecifier(Required) & self.enabled:
            opt_name = self.manager.paramToOption(par_name)
            if opt_name not in opt_counts or opt_counts[opt_name] == 0:
                raise OptionError("Option %r is not specified" % opt_name, opt_name)
    
        return True

    def addObjects(self, dict, source='dict', subsource=None):
        """Přidá na zásobník voleb objekty ze slovníku `dict`

        Rozšíří zásobník voleb o prvky slovníku. Jeho klíče jsou jména voleb
        (options) a hodnoty odpovídají hodnotě volby. Je-li volba vícenásobná
        (tj. specifikátory Multiple nebo JoinSources), považuje se odpovídající
        hodnota ve slovníku za sekvenční kontejner jenž je procházen a jeho
        prvky jsou postupně přidávány na zásobník.

        :Parameters:
            - `dict` - slovník, jehož hodnoty rozšíří zásobník
            - `source` - použitá hodnota zdroje, defaultně 'dict'
            - `subsource` - použitá hodnota podzdroje, defaultně `None`
        """
        multi_options = self.manager.optionsWithSpecifier(Multiple)
        multi_options |= self.manager.optionsWithSpecifier(JoinSources)

        tmp = []
        for opt_name, value in dict.iteritems():
            if opt_name in multi_options:
                if not issequence(value):
                    value = [value]
                for subvalue in value:
                    tmp.append( (opt_name, subvalue, source, subsource) )
            else:
                tmp.append( (opt_name, value, source, subsource) )
        self.extend(tmp)

class _OptionTree(dict):
    pathsep = '.'

    def __init__(self, manager):
        super(_OptionTree, self).__init__()
        self._manager = manager
        self._optionSources = {}

    def nested(self, path=None):
        if path is not None:
            req_path = path.split(self.pathsep)
            req_path_len = len(req_path)
        else:
            req_path = []
            req_path_len = 0
        ret = {}

        def getParentDict(path):
            old_path = []
            parent = ret
            while path:
                parent = parent.setdefault(path[0], {})
                old_path.append(path[0])
                if not isinstance(parent, dict):
                    return None
                path = path[1:]
            return parent

        for key, value in self.iteritems():
            path = key.split(self.pathsep)
            if path[:req_path_len] != req_path:
                continue
            else:
                path = path[req_path_len:]

            where_key = path[-1]
            path = path[:-1]
            where = getParentDict(path)
            if where is None or where_key in where:
                raise ValueError("Cannot branch tree (node %r)" % key)
            where[where_key] = value
        return ret

    def storeValue(self, par_name, value, source):
        specifiers = self._manager.specifiers(par_name)

        # Watch the changes of sources and delete value from previous
        # source
        if self._optionSources.get(par_name, None) != source:
            if par_name in self \
            and JoinSources not in specifiers:
                del self[par_name]
        self._optionSources[par_name] = source

        if JoinSources in specifiers or Multiple in specifiers:
            # Value can have multiple values, so append it to the list of
            # values
            if par_name not in self:
                self[par_name] = []
            lst = self[par_name]
            lst.append(value)
        else:
            # Single value, store it in option tree
            self[par_name] = value

class Extractor(PythonEgg):
    """Rozhraní extraktoru sloužící třídě `Script`

    Umožňuje třídě `Script` implementující rozhraní `ExternalAdapter` používat
    více zdrojů voleb. Každý zdroj voleb je reprezentován jednou třídou
    implementující rozhraní `Extractor`.
    """
    def getSource(self):
        """Vrátí používaný zdroj voleb

        Není-li nastaven, vrátí ``None``.

        :See:
            `Script.getSources`
        """
    
    def setSource(self, source):
        """Nastaví používaný zdroj voleb.

        Pro použití implicitního zdroje, použijte ``source = None``.

        :See:
            `Script.setSources`
        """
    
    def getSourceName(self):
        """Vrátí jméno zdroje

        Jménem zdroje je každý `Extractor` reprezentován v rámci objektu
        `Script`. Umožňuje hromadné nastavování používaných zdrojů.

        :See:
            `Script.setSources`
        """
    
    def extract(self, state):
        """Naplní seznam voleb

        :See:
            `OptionStack.popObjects`
        """
    
    def setManager(self, manager):
        """Umožní extraktoru získat odkaz na instanci `OptionManager`
        """

    def getHelpForOptions(self):
        """Vrátí slovník s nápovědou pro parametry od tohoto extractoru
        """

    def getHelpForExtractor(self):
        """Vrátí řetězec - nápovědu tohoto extractoru
        """


class SimpleScript(ParametrizedObject):
    """Třída reprezentující skript v jazyce Python

    Pro napsání vlastního skriptu je třeba odvodit potomka této třídy a v něm
    předefinovat minimálně následující atributy a metody: `main` a `options`.

    Chybí-li některý parametr určující chování extraktoru, je nahrazen
    odpovídající prázdnou hodnotou.

    :Ivariables:
        - `main` - hlavní metoda skriptu. Více viz `ParametrizedObject`.
        - `options` - atribut typu ``dict`` specifikující popis jednotlivých
          voleb skriptu. Více viz třída `OptionManager`.
        - `shortOpts` -atributy popisující chování extraktoru
          `extractors.CmdlineExtractor`. Atribut `shortOpts` je slovník, jehož
          klíče jsou *jednopísmené zkrácené volby*, hodnoty pak jméno
          odpovídající volby v nezkráceném tvaru.
        - `posOpts` - atributy popisující chování extraktoru
          `extractors.CmdlineExtractor`. `posOpts` pak popisuje *poziční*
          volby předané na příkazové řádce. Jde o seznam jmen jednotlivých
          voleb.
        - `envPrefix` - atribut sloužící pro vytvoření extraktoru
          `extractors.EnvironExtractor`. Seznam určující prefixy, jež lze
          připojit před jméno volby. Takto se získá jméno, jež se hledá mezi
          proměnnými prostředí.
        - `pyFiles` - atributy pro konstruktor extraktoru
          `extractors.PyFileExtractor`. Seznam jmen konfiguračních souborů.  Ve
          jménech jsou znaky tildy (``~``) nahrazeny domácím adresářem
          uživatele.
        - `pyFilesGlobals` - atributy pro konstruktor extraktoru
          `extractors.PyFileExtractor`. Slovník definující globální prostor
          jmen pro spouštění skriptů `pyFiles`.
        - `debug` - je-li ``True``, nebudou použity handlery pro obsluhu chyb a
          výjimky budou vypisovány interpretrem v nezkráceném tvaru.
        - `debugMain` - je-li ``True``, nebude použit handler pro obsluhu chyb
          v hlavní funkci a výjimky budou vypisovány interpretrem v nezkráceném
          tvaru.
        - `_extractors` - seznam používaných extraktorů
        - `_manager` - odkaz na používaný `OptionManager`
    """
    debug = False
    debugMain = False

    options = {}
    optionsDoc = {}

    shortOpts = {}
    posOpts = []
    envPrefix = None
    pyFiles = []
    pyFilesGlobals = None

    def __init__(self, sources={}):
        super(SimpleScript, self).__init__()

        self.createExtractors(**self.extractorsArgs)
        self.setSources(sources)

        self.manager = OptionManager(**self.managerArgs)

    def getExtractorsArgs(self):
        ex_args = {}
        if hasattr(self, 'short_opts'):
            raise AttributeError("Please, use shortOpts instead of short_opts")
        if hasattr(self, 'pos_opts'):
            raise AttributeError("Please, use posOpts instead of pos_opts")
        if hasattr(self, 'env_prefix'):
            raise AttributeError("Please, use envPrefix instead of env_prefix")
        if hasattr(self, 'pyfiles'):
            raise AttributeError("Please, use pyFiles instead of pyfiles")
        if hasattr(self, 'pyfiles_globals'):
            raise AttributeError("Please, use pyFilesGlobals instead of pyfiles_globals")
        ex_args['short_opts'] = self.shortOpts.copy()
        ex_args['pos_opts'] = self.posOpts[:]
        ex_args['env_prefix'] = self.envPrefix
        ex_args['pyfiles'] = self.pyFiles
        ex_args['pyfiles_globals'] = self.pyFilesGlobals
        return ex_args

    def getManagerArgs(self):
        oargs = {}
        oargs['specification'] = self.options.copy()
        oargs['docs'] = self.optionsDoc.copy()
        return oargs

    def _extractionError(self, e):
        """Handler pro výpis chyb při získávání voleb
        """
        if self.debug: raise
        extractorName = ''
        if hasattr(e, 'extractorName'):
            extractorName = "%s: " % e.extractorName
        print >> sys.stderr, 'Script %s: %s%s' % \
                    (self.__class__.__name__, extractorName, str(e))
        sys.exit(-1)
    
    def _conversionError(self, e):
        """Handler pro výpis chyb při konverzi hodnot voleb na objekty
        """
        if self.debug: raise
        optionName = ''
        if hasattr(e, 'optionName'):
            optionName = " '%s'" % e.optionName
        print >> sys.stderr, 'Script %s: Bad option%s: %s: %s' % \
                    (self.__class__.__name__, optionName, e.__class__.__name__, str(e))
        sys.exit(-1)

    def _mainError(self, e):
        """Handler pro výpis chyb v hlavní funkci skriptu
        """
        if self.debugMain: raise
        if not isinstance(e, OptionError):
            print >> sys.stderr, 'Script %s: %s: %s' % \
                        (self.__class__.__name__, e.__class__.__name__, str(e))
        else:
            # TODO: Move into self._extractionError()
            print >> sys.stderr, 'Script %s: %s' % \
                        (self.__class__.__name__, str(e))
        sys.exit(-1)
    
    def run(self, sources=None):
        """Vykoná skript, umožňuje nastavit zdroje

        Pokud je `sources` různé od ``None``, provede se nejprve uchování
        starých zdrojů, následně se nastaví zdroje na `sources`, vykoná se
        hlavní funkce `main` a následně se obnoví zdroje na původní hodnotu.

        :See:
            `getSources`, `setSources`
        """
        if sources is not None:
            old_sources = self.getSources()
            self.setSources(sources)
        else:
            old_sources = None

        retval = super(SimpleScript, self).run()

        if old_sources is not None:
            self.setSources(old_sources)

        return retval

    def createState(self):
        self.state = OptionStack(self.manager)
        self.state.disableAll()

        self.extractOptions(self.state)

    def getExtractors(self):
        """Vrátí seznam extraktorů
        """
        return self._extractors
    
    def createExtractors(self, short_opts, pos_opts, env_prefix, pyfiles, pyfiles_globals):
        """Vytvoří extraktory

        Implicitně vytváří následující extraktory (pomocí argumentů v závorce):

            1. `extractors.EnvironExtractor` (`env_prefix`) - extraktor pro
               získávání voleb z proměnných prostředí.
            2. `extractors.PyFileExtractor` (`pyfiles_globals`, `pyfiles`) -
               extraktor pro získávání voleb z konfiguračních souborů v jazyce
               Python.
            3. `extractors.CmdlineExtractor` (`short_opts`, `pos_opts`) -
               extraktor pro získávání voleb z argumentů předávaných na příkazové
               řádce.

        Extraktory jsou uchovány v atributy `_extractors` a při volání metody
        `extractOptions` jsou použity v uvedeném pořadí.
        """
        from svc.scripting.extractors import CmdlineExtractor, EnvironExtractor, PyFileExtractor
        env     = self._extractor_env     = EnvironExtractor(env_prefix)
        pyfiles = self._extractor_pyfiles = PyFileExtractor(pyfiles_globals, pyfiles)
        argv    = self._extractor_argv    = CmdlineExtractor(short_opts, pos_opts)
        self._extractors = [env, pyfiles, argv]
    
    def getSources(self):
        """Vrátí nastavené zdroje

        Zdroje extraktorů s implicitní hodnotou (tj. `Extractor.getSource`
        vrátí ``None``) nejsou ve výsledku zahrnuty.
        """
        ret = {}
        for e in self.getExtractors():
            name = e.getSourceName()
            source = e.getSource()
            if source is not None:
                ret[name] = source
        return ret

    def setSources(self, sources):
        """Nastaví zdroje používané extraktory

        Nejprve jsou zdroje všech extraktorů nastaveny na implicitní hodotu
        (tj. ``None``) a poté jsou brány páry ``jméno:hodnota`` slovníku
        `sources` a extraktoru jehož `Extractor.getSourceName` vrátí ``jméno``
        je nastaven zdroj ``hodnota``.
        """
        extractors = {}
        for e in self.getExtractors():
            name = e.getSourceName()
            extractors[name] = e
            e.setSource(None)
        for name, source in sources.iteritems():
            e = extractors[name]
            e.setSource(source)
    
    def getManager(self):
        """Vrátí používaní `OptionManager`

        :See:
            `_manager`
        """
        return self._manager
    
    def setManager(self, manager):
        """Nastaví používaný `OptionManager`

        Tento `manager` ja rovněž nastaven všem extraktorům.

        :See:
            `_manager`, `Extractor.setManager`
        """
        self._manager = manager
        for e in self.getExtractors():
            e.setManager(manager)

    def extractOptions(self, state):
        """Vrátí seznam voleb ve formě řetězců

        Prochází jednotlivé extraktory, volá jejich metody `Extractor.extract`
        a vrátí sjednocení jejich návratových hodnot.

        :See:
            `OptionStack.popObjects`
        """
        for e in self.getExtractors():
            try:
                e.extract(state)
            except:
                exc = sys.exc_info()[1]
                exc.extractorName = e.getSourceName()
                raise
    
    def getScriptFile(self):
        """Vrátí soubor, v němž je skript definován
        """
        #return inspect.getmodule(self).__file__
        return sys.argv[0]

    def getHelpForFunc(self):
        """Vrátí řetězec s nápovědou pro asociovanou funkci
        """
        return self.main.__doc__

class Script(SimpleScript):
    _SCREEN_WIDTH = 80

    def __init__(self, sources={}):
        super(Script, self).__init__(sources)
        self.createLogger()

    def getExtractorsArgs(self):
        ex_args = super(Script, self).getExtractorsArgs()
        ex_args['short_opts'].update({
            'v': 'verbose',
            'h': 'help',
        })
        return ex_args

    def getManagerArgs(self):
        m_args = super(Script, self).getManagerArgs()
        m_args['specification'].update({
            '__premain__.pyfile': (Multiple, String),
            '__premain__.logging.verbose_level': String,
            '__premain__.logging.verbose': (Multiple, Bool),
            '__premain__.help': Flag,
            '__premain__.debug': Flag,
        })
        m_args['docs'].update({
            'pyfile': "Additional configuration file to include",
            'verbose_level': "Precise verbose level (DEBUG, INFO, WARNING, ERROR)",
            'verbose': "Verbose output",
            'help': 'Prints help message',
            'debug': 'Turn on printing of tracebacks',
        })
        return m_args

    def premain(self, help=False, pyfile=[], logging={}, debug=False, **kwargs):
        # Setup Script logging system
        self.setupLogger(**logging)

        if help:
            self.printHelp()
            sys.exit()

        if debug:
            self.debug = self.debugMain = True

        # Add extra PyFiles to the PyFileExtractor instance and extend current
        # state with extracted values
        orig_source = self._extractor_pyfiles.source
        if orig_source is None:
            orig_source = []
        self._extractor_pyfiles.source = orig_source + pyfile
        self._extractor_pyfiles.extract(self.state)

        return super(Script, self).premain(**kwargs)

    def createLogger(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.addHandler(logging.StreamHandler(sys.stderr))

    def setupLogger(self, verbose_level=logging.WARNING, verbose=[]):
        try:
            verbose_level = int(verbose_level)
        except ValueError:
            verbose_level = verbose_level.upper()
            try:
                verbose_level = logging._levelNames[verbose_level]
            except KeyError:
                raise ValueError("Unknown verbose_level: %r" % verbose_level)
        for i in verbose:
            if i: verbose_level -= 10
        verbose_level = max(verbose_level, 1)
        self.logger.setLevel(verbose_level)

    def _getMainOptions(self):
        script_params = self.manager.params()
        script_params -= self.manager.paramsChildren('__premain__')
        script_options = [self.manager.paramToOption(p) for p in script_params]
        return script_options

    def _getPremainOptions(self):
        other_params = self.manager.paramsChildren('__premain__')
        other_options = [self.manager.paramToOption(p) for p in other_params]
        return other_options

    def printHelp(self):
        m = HelpManager(self.manager, self.extractors, screenWidth=self._SCREEN_WIDTH)

        script_file = os.path.basename(self.scriptFile)

        m.printUsage(script_file, self.posOpts, self.__class__)

        script_options = self._getMainOptions()
        m.printHelpDictOptionsHdr(script_options, 'Options', newline=True)

        other_options = self._getPremainOptions()
        if other_options:
            m.printHelpDictOptionsHdr(other_options, 'Other options')

class ExScript(Script):
    """Třída pro výkoné skripty v jazyce Python

    Automaticky umožňuje práci s logováním a více příkazy.

    :Ivariables:
        - `defaultCommand` - výchozí příkaz, pokud nejsou specifikovány jiné
          příkazy
    """
    CommandParam = (Multiple, sym('_CommandParam'), String)
    defaultCommand = None

    def __init__(self, *args, **kwargs):
        self._cmdPosOpts = {}
        super(ExScript, self).__init__(*args, **kwargs)

    def createExtractors(self, **kwargs):
        from svc.scripting.extractors import CmdPosOptsExtractor
        super(ExScript, self).createExtractors(**kwargs)
        cmdPos     = self._extractor_cmdPos     = CmdPosOptsExtractor(self)
        self._extractors.append(cmdPos)

    def setCmdPosOpts(self, cmdPosOpts):
        self._cmdPosOpts = cmdPosOpts.copy()

    def getCmdPosOpts(self):
        return self._cmdPosOpts

    def _modifyPosOpts(self, pos_opts):
        has_cpo = False
        ret = []
        for i in pos_opts:
            if isinstance(i, dict):
                if has_cpo:
                    raise ValueError('You can use only one command specific positional option part')
                has_cpo = True
                self.cmdPosOpts = i
                ret.append('_command_pos_opts')
                ret.append(Ellipsis)
            elif i is Ellipsis and has_cpo:
                raise ValueError("You can't use Ellipsis together with command specific positional options")
            else:
                ret.append(i)
        return ret

    def getExtractorsArgs(self):
        args = super(ExScript, self).getExtractorsArgs()
        args['pos_opts'] = self._modifyPosOpts(args['pos_opts'])
        return args

    def getManagerArgs(self):
        m_args = super(ExScript, self).getManagerArgs()
        m_args['specification'].update({
            '__premain__._command_pos_opts': (Multiple, String),
        })
        return m_args

    def getCommandOption(self):
        command_options = self.manager.paramsWithSpecifier('_CommandParam')
        if len(command_options) != 1:
            raise ValueError("There must be exactly one ExScript.CommandParam option")
        return command_options.pop()

    def getCommandValue(self):
        commandOption = self.commandOption
        enabled = self.state.enabled
        try:
            self.state.disableAll()
            self.state.enable([commandOption])
            try:
                return self.state.getObjects()[commandOption]
            except KeyError:
                # TODO: Change type of exception
                raise ValueError('Command not specified')
        finally:
            self.state.disableExcept(enabled)

    def premain(self, _command_pos_opts=[], **kwargs):
        cont = super(ExScript, self).premain(**kwargs)
        # Enable all parameters, which will be passed to main() method ...
        self.state.enableAll()
        # ... and disable parameters, which belongs to any command
        for command in self.commands:
            params = self.state.manager.paramsChildren(command)
            self.state.disable(params)
        return cont

    def main(self, **kwargs):
        commands = []
        if self.defaultCommand:
            commands.append(self.defaultCommand)
        # Get commands and invoke this commands via invokeCommand()
        command_parameters = self.manager.paramsWithSpecifier('_CommandParam')
        if command_parameters:
            new_commands = []
            for param in command_parameters:
                if param in kwargs:
                    new_commands.extend(kwargs.pop(param))
            if new_commands:
                commands[:] = new_commands
        if kwargs:
            raise TypeError("Not supported main() parameters: %s" % ', '.join(kwargs.keys()))
        if commands:
            for c in commands:
                self.invokeCommand(c)

    def _methodForCommand(self, command):
        method = getattr(self, command, None)
        if not self.isCommand(method):
            raise ValueError("Unknown command %r" % command)
        return method

    def invokeCommand(self, command, **kwargs):
        method = self._methodForCommand(command)
        params = self.manager.paramsChildren(command)

        self.state.enable(params)
        self.state.disable('%s.%s' % (command, arg) for arg in kwargs)
        params_values = self.state.getObjects()
        self.state.disable(params)

        method_kwargs = params_values.get(command, {})
        method_kwargs.update(kwargs)

        return method(**method_kwargs)

    @staticmethod
    def command(func):
        func._ExScript_command = True
        return func

    @staticmethod
    def isCommand(func):
        return getattr(func, '_ExScript_command', False)

    def getCommands(self):
        ret = set()
        for class_ in self.__class__.__mro__:
            for name, func in vars(class_).iteritems():
                if self.isCommand(func):
                    ret.add(name)
        return ret

    def _getMainOptions(self):
        script_params = self.manager.params()
        script_params -= self.manager.paramsChildren('__premain__')
        for command in self.commands:
            script_params -= self.manager.paramsChildren(command)
        script_options = [self.manager.paramToOption(p) for p in script_params]
        return script_options

    def printHelp(self):
        m = HelpManager(self.manager, self.extractors, screenWidth=self._SCREEN_WIDTH)

        script_file = os.path.basename(self.scriptFile)
        m.printUsage(script_file, self.posOpts, self.__class__)

        script_options = self._getMainOptions()
        m.printHelpDictOptionsHdr(script_options, 'Options', newline=True)

        if self.commands:
            m.printHeader('Commands')
            for command in sorted(self.commands):
                method = self._methodForCommand(command)
                m.printHelpForCommand(command, method)

        other_options = [o for o in self._getPremainOptions() if not o.startswith('_')]
        if other_options:
            m.printHelpDictOptionsHdr(other_options, 'Other options')

