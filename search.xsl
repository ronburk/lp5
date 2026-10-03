<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:exsl="http://exslt.org/common"
    exclude-result-prefixes="exsl">

    <xsl:output method="xml" encoding="UTF-8" indent="no"/>

    <xsl:template match="/">
        <xsl:variable name="weave" select="lp5-search-input/lp5-weave"/>
        <xsl:variable name="mode" select="lp5-search-input/@mode"/>
        <xsl:if test="count($weave) != 1 or count($weave/articles) != 1">
            <xsl:message terminate="yes">search: expected lp5-weave with exactly one direct articles child.</xsl:message>
        </xsl:if>
        <xsl:if test="not($mode = 'any' or $mode = 'all') or not(lp5-search-input/query/term)">
            <xsl:message terminate="yes">search: invalid query.</xsl:message>
        </xsl:if>

        <xsl:variable name="canonical-query">
            <terms>
                <xsl:for-each select="lp5-search-input/query/term">
                    <xsl:variable name="value"
                        select="translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')"/>
                    <xsl:if test="$value = ''">
                        <xsl:message terminate="yes">search: empty search term.</xsl:message>
                    </xsl:if>
                    <term><xsl:value-of select="$value"/></term>
                </xsl:for-each>
            </terms>
        </xsl:variable>
        <xsl:variable name="terms"
            select="exsl:node-set($canonical-query)/terms/term[not(. = preceding-sibling::term)]"/>

        <xsl:variable name="result-tree">
            <results>
                <xsl:for-each select="$weave/articles/article">
                    <xsl:variable name="fields"
                        select="heading | keywords/li | section[@data-lp5-kind='explanation'] | section[@data-lp5-kind='code']/name | section[@data-lp5-kind='code']/code"/>
                    <xsl:variable name="matched-terms">
                        <terms>
                            <xsl:for-each select="$terms">
                                <xsl:variable name="term" select="string(.)"/>
                                <xsl:if test="$fields[contains(translate(normalize-space(string(.)), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), $term)]">
                                    <term><xsl:value-of select="$term"/></term>
                                </xsl:if>
                            </xsl:for-each>
                        </terms>
                    </xsl:variable>
                    <xsl:variable name="matched"
                        select="exsl:node-set($matched-terms)/terms/term"/>
                    <xsl:if test="($mode = 'any' and count($matched) &gt; 0) or ($mode = 'all' and count($matched) = count($terms))">
                        <article file="{@file}" score="{count($matched)}">
                            <matches>
                                <xsl:for-each select="$matched">
                                    <xsl:variable name="term" select="string(.)"/>
                                    <xsl:for-each select="$fields[contains(translate(normalize-space(string(.)), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), $term)]">
                                        <xsl:variable name="text" select="normalize-space(string(.))"/>
                                        <xsl:variable name="canonical-text"
                                            select="translate($text, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')"/>
                                        <xsl:variable name="match-start"
                                            select="string-length(substring-before($canonical-text, $term)) + 1"/>
                                        <xsl:variable name="window">
                                            <xsl:choose>
                                                <xsl:when test="string-length($term) &gt; 200">
                                                    <xsl:value-of select="string-length($term)"/>
                                                </xsl:when>
                                                <xsl:otherwise>200</xsl:otherwise>
                                            </xsl:choose>
                                        </xsl:variable>
                                        <xsl:variable name="context-before"
                                            select="floor((number($window) - string-length($term)) div 2)"/>
                                        <xsl:variable name="start">
                                            <xsl:choose>
                                                <xsl:when test="$match-start &gt; $context-before">
                                                    <xsl:value-of select="$match-start - $context-before"/>
                                                </xsl:when>
                                                <xsl:otherwise>1</xsl:otherwise>
                                            </xsl:choose>
                                        </xsl:variable>
                                        <xsl:text>&#10;          </xsl:text>
                                        <match term="{$term}">
                                            <xsl:attribute name="field">
                                                <xsl:call-template name="field-name"/>
                                            </xsl:attribute>
                                            <excerpt truncated-before="{number($start) &gt; 1}"
                                                truncated-after="{string-length($text) &gt; number($start) + number($window) - 1}">
                                                <xsl:if test="number($start) &gt; 1">…</xsl:if>
                                                <xsl:value-of select="substring($text, number($start), number($window))"/>
                                                <xsl:if test="string-length($text) &gt; number($start) + number($window) - 1">…</xsl:if>
                                            </excerpt>
                                        </match>
                                    </xsl:for-each>
                                </xsl:for-each>
                                <xsl:if test="$matched">
                                    <xsl:text>&#10;        </xsl:text>
                                </xsl:if>
                            </matches>
                        </article>
                    </xsl:if>
                </xsl:for-each>
            </results>
        </xsl:variable>
        <xsl:variable name="results" select="exsl:node-set($result-tree)/results/article"/>
        <lp5-search version="1" mode="{$mode}" total="{count($results)}">
            <query>
                <xsl:for-each select="$terms">
                    <xsl:text>&#10;    </xsl:text>
                    <term><xsl:value-of select="."/></term>
                </xsl:for-each>
                <xsl:if test="$terms">
                    <xsl:text>&#10;  </xsl:text>
                </xsl:if>
            </query>
            <results>
                <xsl:for-each select="$results">
                    <xsl:sort select="@score" data-type="number" order="descending"/>
                    <xsl:text>&#10;    </xsl:text>
                    <xsl:copy-of select="."/>
                </xsl:for-each>
                <xsl:if test="$results">
                    <xsl:text>&#10;  </xsl:text>
                </xsl:if>
            </results>
        </lp5-search>
        <xsl:text>&#10;</xsl:text>
    </xsl:template>

    <xsl:template name="field-name">
        <xsl:choose>
            <xsl:when test="self::heading">heading</xsl:when>
            <xsl:when test="self::li and parent::keywords">keyword</xsl:when>
            <xsl:when test="self::section[@data-lp5-kind='explanation']">explanation</xsl:when>
            <xsl:when test="self::name and parent::section[@data-lp5-kind='code']">code-name</xsl:when>
            <xsl:when test="self::code and parent::section[@data-lp5-kind='code']">code</xsl:when>
        </xsl:choose>
    </xsl:template>
</xsl:stylesheet>
