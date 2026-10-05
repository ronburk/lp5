<?xml version="1.0" encoding="UTF-8"?>
<!-- Remove one child link and return the updated parent article. -->
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:exsl="http://exslt.org/common"
    extension-element-prefixes="exsl">

    <xsl:import href="add-article.xsl"/>

    <xsl:output method="xml" encoding="UTF-8" indent="no"/>

    <xsl:param name="article_id" select="'__ARTICLE_ID_REQUIRED__'"/>
    <xsl:param name="parent_id" select="'__PARENT_ID_REQUIRED__'"/>

    <xsl:template match="/">
        <xsl:variable name="article"
            select="/lp5-weave/articles/article[@file = $article_id]"/>
        <xsl:variable name="parent"
            select="/lp5-weave/articles/article[@file = $parent_id]"/>

        <xsl:if test="$article_id = '__ARTICLE_ID_REQUIRED__' or
                $parent_id = '__PARENT_ID_REQUIRED__'">
            <xsl:message terminate="yes">remove-article.xsl requires article_id and parent_id parameters.</xsl:message>
        </xsl:if>
        <xsl:if test="count($article) != 1 or count($parent) != 1">
            <xsl:message terminate="yes">article_id and parent_id must identify exactly one article in weave.xml.</xsl:message>
        </xsl:if>
        <xsl:if test="$article_id = /lp5-weave/articles/article[1]/@file">
            <xsl:message terminate="yes">cannot remove the root article.</xsl:message>
        </xsl:if>
        <xsl:if test="$article/children/child">
            <xsl:message terminate="yes">cannot remove an article that has children.</xsl:message>
        </xsl:if>
        <xsl:if test="count(/lp5-weave/articles/article/children/child[@file = $article_id]) != 1 or
                count($parent/children/child[@file = $article_id]) != 1">
            <xsl:message terminate="yes">article must have exactly one link from its parent.</xsl:message>
        </xsl:if>

        <xsl:variable name="updated-parent">
            <template>
                <xsl:text>&#10;    </xsl:text>
                <children>
                    <xsl:for-each select="$parent/children/child[@file != $article_id]">
                        <xsl:text>&#10;        </xsl:text>
                        <li id="{@file}"/>
                    </xsl:for-each>
                    <xsl:if test="$parent/children/child[@file != $article_id]">
                        <xsl:text>&#10;    </xsl:text>
                    </xsl:if>
                </children>
                <xsl:for-each select="$parent/*[not(self::children)]">
                    <xsl:text>&#10;    </xsl:text>
                    <xsl:apply-templates select="." mode="copy-parent"/>
                </xsl:for-each>
                <xsl:text>&#10;</xsl:text>
            </template>
        </xsl:variable>

        <xsl:call-template name="validate-article">
            <xsl:with-param name="document" select="exsl:node-set($updated-parent)"/>
            <xsl:with-param name="location" select="$parent_id"/>
        </xsl:call-template>
        <xsl:copy-of select="exsl:node-set($updated-parent)/*"/>
        <xsl:text>&#10;</xsl:text>
    </xsl:template>
</xsl:stylesheet>
