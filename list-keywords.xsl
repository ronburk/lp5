<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:exsl="http://exslt.org/common"
    exclude-result-prefixes="exsl">

    <xsl:output method="xml" encoding="UTF-8" indent="no"/>
    <xsl:key name="keywords-by-value" match="/keyword-index/keyword" use="@value"/>

    <xsl:template match="/">
        <xsl:variable name="weave" select="lp5-weave"/>
        <xsl:if test="count($weave) != 1 or count($weave/articles) != 1">
            <xsl:message terminate="yes">list-keywords: expected lp5-weave with exactly one direct articles child.</xsl:message>
        </xsl:if>
        <xsl:variable name="index-tree">
            <keyword-index>
                <xsl:choose>
                    <xsl:when test="$weave/keyword-index">
                        <xsl:copy-of select="$weave/keyword-index/keyword"/>
                    </xsl:when>
                    <xsl:otherwise>
                        <!-- Match search-keywords compatibility with older fresh caches. -->
                        <xsl:for-each select="$weave/articles/article/keywords/li[normalize-space(.) != '']">
                            <keyword value="{translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')}">
                                <article file="{../../@file}"/>
                            </keyword>
                        </xsl:for-each>
                    </xsl:otherwise>
                </xsl:choose>
            </keyword-index>
        </xsl:variable>
        <xsl:variable name="keywords" select="exsl:node-set($index-tree)/keyword-index/keyword[@value != ''][generate-id() = generate-id(key('keywords-by-value', @value)[1])]"/>
        <lp5-keywords version="1" total="{count($keywords)}">
            <xsl:for-each select="$keywords">
                <xsl:sort select="@value" data-type="text" order="ascending"/>
                <!-- Count article records, so repeated memberships cannot inflate counts. -->
                <xsl:variable name="files" select="key('keywords-by-value', @value)/article/@file"/>
                <keyword article-count="{count($weave/articles/article[@file = $files])}"><xsl:value-of select="@value"/></keyword>
            </xsl:for-each>
        </lp5-keywords>
        <xsl:text>&#10;</xsl:text>
    </xsl:template>
</xsl:stylesheet>
