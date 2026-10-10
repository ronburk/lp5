<?xml version="1.0" encoding="UTF-8"?>
<!--
     add-article.xsl - add one article to a parent's child list.

     Run from the project root, with weave.xml generated from the current
     project. articles_dir is a filesystem path relative to the working
     directory (or absolute); article_file is the absolute URI of the staged
     article supplied by the launcher. It is independent of the index location.

     This stylesheet produces the updated parent article. The lp5 add-article
     command stages this result together with the new article and installs both
     in the source directory. The launcher supplies my:ls() so filename
     selection can check directory entries without opening candidate articles.
-->
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:my="http://example.com/lp5ext"
    exclude-result-prefixes="my">

    <xsl:import href="tangle.xsl"/>

    <xsl:output method="xml" encoding="UTF-8" indent="no"/>

    <xsl:param name="parent_id" select="'__PARENT_ID_REQUIRED__'"/>
    <xsl:param name="before_child_id" select="''"/>
    <xsl:param name="articles_dir" select="'__ARTICLES_DIR_REQUIRED__'"/>
    <xsl:param name="article_file" select="'__ARTICLE_FILE_REQUIRED__'"/>

    <xsl:template match="/">
        <xsl:if test="$parent_id = '__PARENT_ID_REQUIRED__' or
                $articles_dir = '__ARTICLES_DIR_REQUIRED__' or
                $article_file = '__ARTICLE_FILE_REQUIRED__'">
            <xsl:message terminate="yes">add-article.xsl requires parent_id, articles_dir, and article_file parameters.</xsl:message>
        </xsl:if>

        <xsl:variable name="parent"
            select="/lp5-weave/articles/article[@file = $parent_id]"/>
        <xsl:if test="count($parent) != 1">
            <xsl:message terminate="yes">parent_id must identify exactly one article in weave.xml.</xsl:message>
        </xsl:if>

        <xsl:if test="string-length($before_child_id) and
                count($parent/children/child[@file = $before_child_id]) != 1">
            <xsl:message terminate="yes">before_child_id must identify exactly one direct child of parent_id.</xsl:message>
        </xsl:if>

        <xsl:variable name="new-article" select="document($article_file, /)"/>
        <xsl:call-template name="validate-article">
            <xsl:with-param name="document" select="$new-article"/>
            <xsl:with-param name="location" select="$article_file"/>
        </xsl:call-template>

        <xsl:variable name="available-articles"
            select="my:ls($articles_dir)[@type = 'file']"/>
        <xsl:variable name="new-filename">
            <xsl:call-template name="new-article-filename">
                <xsl:with-param name="available-articles" select="$available-articles"/>
            </xsl:call-template>
        </xsl:variable>

        <template>
            <xsl:text>&#10;    </xsl:text>
            <!--
                 weave.xsl emits a children record even when the source
                 article has no child links. Iterating its child entries
                 therefore handles both an empty list and a populated one.
             -->
            <children>
                <xsl:if test="not(string-length($before_child_id))">
                    <xsl:text>&#10;        </xsl:text>
                    <li id="{$new-filename}"/>
                </xsl:if>
                <xsl:for-each select="$parent/children/child">
                    <xsl:if test="@file = $before_child_id">
                        <xsl:text>&#10;        </xsl:text>
                        <li id="{$new-filename}"/>
                    </xsl:if>
                    <xsl:text>&#10;        </xsl:text>
                    <li id="{@file}"/>
                </xsl:for-each>
                <xsl:text>&#10;    </xsl:text>
            </children>

            <!--
                 The children record above is derived index data, so rebuild
                 it as source <li> links. Copy every other article element
                 from the weave record. Keeping this selection open-ended
                 prevents new article fields (such as <keywords>) from being
                 silently lost when this operation rewrites the parent.
             -->
            <xsl:for-each select="$parent/*[not(self::children)]">
                <xsl:text>&#10;    </xsl:text>
                <xsl:apply-templates select="." mode="copy-parent"/>
            </xsl:for-each>
            <xsl:text>&#10;</xsl:text>
        </template>
        <xsl:text>&#10;</xsl:text>
    </xsl:template>

    <!--
         weave.xml's code is text, regardless of whether its source was CDATA.
         Re-emit text inside code sections as CDATA so the result is a valid
         source article. Explanation markup, including inline <code>, is copied
         normally.
    -->
    <xsl:template match="@*|node()" mode="copy-parent">
        <xsl:copy>
            <xsl:apply-templates select="@*|node()" mode="copy-parent"/>
        </xsl:copy>
    </xsl:template>

    <xsl:template match="code[parent::section[@data-lp5-kind = 'code']]"
                  mode="copy-parent">
        <xsl:copy>
            <xsl:apply-templates select="node()" mode="copy-code"/>
        </xsl:copy>
    </xsl:template>

    <xsl:template match="text()" mode="copy-code">
        <xsl:text disable-output-escaping="yes">&lt;![CDATA[</xsl:text>
        <xsl:call-template name="emit-cdata-text">
            <xsl:with-param name="text" select="."/>
        </xsl:call-template>
        <xsl:text disable-output-escaping="yes">]]&gt;</xsl:text>
    </xsl:template>

    <xsl:template match="*" mode="copy-code">
        <xsl:copy-of select="."/>
    </xsl:template>

    <!-- Split CDATA terminators so arbitrary code text remains well-formed. -->
    <xsl:template name="emit-cdata-text">
        <xsl:param name="text"/>
        <xsl:choose>
            <xsl:when test="contains($text, ']]&gt;')">
                <xsl:value-of select="substring-before($text, ']]&gt;')"
                              disable-output-escaping="yes"/>
                <xsl:text disable-output-escaping="yes">]]]]&gt;&lt;![CDATA[&gt;</xsl:text>
                <xsl:call-template name="emit-cdata-text">
                    <xsl:with-param name="text" select="substring-after($text, ']]&gt;')"/>
                </xsl:call-template>
            </xsl:when>
            <xsl:otherwise>
                <xsl:value-of select="$text" disable-output-escaping="yes"/>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>

    <!-- Called with weave.xml as the source. Returns a basename such as 19.lp5. -->
    <xsl:template name="new-article-filename">
        <xsl:param name="available-articles"/>

        <!-- Select the largest numeric article filename from the weave. -->
        <xsl:variable name="max-id">
            <xsl:for-each select="/lp5-weave/articles/article[
                substring-after(@file, '.lp5') = '' and
                string-length(substring-before(@file, '.lp5')) &gt; 0 and
                translate(substring-before(@file, '.lp5'), '0123456789', '') = '']">
                <xsl:sort select="number(substring-before(@file, '.lp5'))"
                          data-type="number" order="descending"/>
                <xsl:if test="position() = 1">
                    <xsl:value-of select="number(substring-before(@file, '.lp5'))"/>
                </xsl:if>
            </xsl:for-each>
        </xsl:variable>

        <xsl:call-template name="try-article-filename">
            <xsl:with-param name="available-articles" select="$available-articles"/>
            <xsl:with-param name="candidate"
                select="number(concat('0', string($max-id))) + 1"/>
        </xsl:call-template>
    </xsl:template>

    <!--
         Use the source-directory inventory for existence checks, so malformed
         article content cannot make an occupied filename look available.
         XSLT 1.0 numbers also have finite integer precision, so extremely large
         numeric IDs are outside this algorithm's range.
    -->
    <xsl:template name="try-article-filename">
        <xsl:param name="available-articles"/>
        <xsl:param name="candidate"/>

        <xsl:variable name="filename" select="concat($candidate, '.lp5')"/>

        <xsl:choose>
            <xsl:when test="$available-articles[@name = $filename]">
                <xsl:call-template name="try-article-filename">
                    <xsl:with-param name="available-articles" select="$available-articles"/>
                    <xsl:with-param name="candidate" select="$candidate + 1"/>
                </xsl:call-template>
            </xsl:when>
            <xsl:otherwise>
                <xsl:value-of select="$filename"/>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>

</xsl:stylesheet>
