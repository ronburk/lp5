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
            <xsl:message terminate="yes">search-keywords: expected lp5-weave with exactly one direct articles child.</xsl:message>
        </xsl:if>
        <xsl:if test="not($mode = 'any' or $mode = 'all') or not(lp5-search-input/query/keyword)">
            <xsl:message terminate="yes">search-keywords: invalid query.</xsl:message>
        </xsl:if>
        <xsl:variable name="canonical-query">
            <query>
                <xsl:for-each select="lp5-search-input/query/keyword">
                    <xsl:variable name="value" select="translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')"/>
                    <xsl:if test="$value = ''">
                        <xsl:message terminate="yes">search-keywords: empty keyword.</xsl:message>
                    </xsl:if>
                    <keyword><xsl:value-of select="$value"/></keyword>
                </xsl:for-each>
            </query>
        </xsl:variable>
        <!-- Deduplicate after canonicalization, retaining first query occurrence. -->
        <xsl:variable name="terms" select="exsl:node-set($canonical-query)/query/keyword[not(. = preceding-sibling::keyword)]"/>
        <xsl:variable name="index-tree">
            <keyword-index>
                <xsl:choose>
                    <xsl:when test="$weave/keyword-index">
                        <xsl:copy-of select="$weave/keyword-index/keyword"/>
                    </xsl:when>
                    <xsl:otherwise>
                        <!-- A fresh cache from an older weave may lack the new index. -->
                        <xsl:for-each select="$weave/articles/article/keywords/li[normalize-space(.) != '']">
                            <keyword value="{translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')}">
                                <article file="{../../@file}"/>
                            </keyword>
                        </xsl:for-each>
                    </xsl:otherwise>
                </xsl:choose>
            </keyword-index>
        </xsl:variable>
        <xsl:variable name="index" select="exsl:node-set($index-tree)/keyword-index"/>
        <xsl:variable name="result-tree">
            <results>
                <xsl:for-each select="$weave/articles/article">
                    <xsl:variable name="file" select="@file"/>
                    <!-- Count unique query terms, never duplicate index memberships. -->
                    <xsl:variable name="matched" select="$terms[. = $index/keyword[article/@file = $file]/@value]"/>
                    <xsl:variable name="score" select="count($matched)"/>
                    <xsl:if test="($mode = 'any' and $score &gt; 0) or ($mode = 'all' and $score = count($terms))">
                        <article file="{@file}" score="{$score}">
                            <matched-keywords><xsl:copy-of select="$matched"/></matched-keywords>
                            <xsl:if test="heading">
                                <heading><xsl:value-of select="normalize-space(string(heading))"/></heading>
                            </xsl:if>
                            <xsl:if test="section[@data-lp5-kind='code']">
                                <code-name><xsl:value-of select="normalize-space(string(section[@data-lp5-kind='code']/name))"/></code-name>
                            </xsl:if>
                            <xsl:if test="section[@data-lp5-kind='explanation']">
                                <xsl:variable name="text" select="normalize-space(string(section[@data-lp5-kind='explanation']))"/>
                                <excerpt truncated="{string-length($text) &gt; 200}"><xsl:value-of select="substring($text, 1, 200)"/></excerpt>
                            </xsl:if>
                        </article>
                    </xsl:if>
                </xsl:for-each>
            </results>
        </xsl:variable>
        <xsl:variable name="results" select="exsl:node-set($result-tree)/results/article"/>
        <lp5-keyword-search version="1" mode="{$mode}" total="{count($results)}">
            <query><xsl:copy-of select="$terms"/></query>
            <results>
                <!-- Stable numeric sort keeps weave order for equal scores. -->
                <xsl:for-each select="$results">
                    <xsl:sort select="@score" data-type="number" order="descending"/>
                    <xsl:copy-of select="."/>
                </xsl:for-each>
            </results>
        </lp5-keyword-search>
        <xsl:text>&#10;</xsl:text>
    </xsl:template>
</xsl:stylesheet>
