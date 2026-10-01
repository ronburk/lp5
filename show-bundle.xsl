<?xml version="1.0" encoding="UTF-8"?>
<!--
     show-bundle.xsl - list bundle names or extract one bundle from a weave.

     Omit code_name to list names. Supply a string (including an empty string
     for unnamed code) to extract that bundle.

     Extraction contains only matching code sections, in article/weave order.
     Each bundle member is the original code section, with an article
     attribute added to identify its source. Explanations are excluded. An
     empty bundle means no matching code sections were found.
-->
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:exsl="http://exslt.org/common"
    exclude-result-prefixes="exsl">

    <!-- Avoid pretty-printing whitespace into copied code content. -->
    <xsl:output method="xml" encoding="UTF-8" indent="no"/>

    <!-- An empty node-set distinguishes omission from every supplied string. -->
    <xsl:param name="code_name" select="/.."/>

    <xsl:template match="/">
        <xsl:if test="count(lp5-weave) != 1 or count(lp5-weave/bundles) != 1">
            <xsl:message terminate="yes">show-bundle: expected lp5-weave with exactly one direct bundles child.</xsl:message>
        </xsl:if>

        <xsl:choose>
            <xsl:when test="exsl:object-type($code_name) = 'node-set'">
                <bundles>
                    <xsl:for-each select="lp5-weave/bundles/bundle[not(@name = preceding-sibling::bundle/@name)]">
                        <bundle name="{@name}"/>
                    </xsl:for-each>
                </bundles>
                <xsl:text>&#10;</xsl:text>
            </xsl:when>
            <xsl:otherwise>
                <xsl:call-template name="show-bundle"/>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>

    <xsl:template name="show-bundle">
        <xsl:variable name="canonical-name" select="normalize-space($code_name)"/>
        <xsl:variable name="bundle"
            select="/lp5-weave/bundles/bundle[@name = $canonical-name]"/>

        <bundle name="{$canonical-name}">
            <xsl:for-each select="$bundle/section">
                <!-- Preserve the on-disk code-section representation. -->
                <xsl:text>&#10;  </xsl:text>
                <xsl:variable name="article-file" select="@article"/>
                <section data-lp5-kind="code" article="{$article-file}">
                    <!-- Format the section metadata, but copy code unchanged. -->
                    <xsl:text>&#10;    </xsl:text>
                    <xsl:copy-of select="/lp5-weave/articles/article[@file = $article-file]/section[@data-lp5-kind = 'code'][normalize-space(name) = $canonical-name]/name"/>
                    <xsl:text>&#10;    </xsl:text>
                    <xsl:copy-of select="/lp5-weave/articles/article[@file = $article-file]/section[@data-lp5-kind = 'code'][normalize-space(name) = $canonical-name]/code"/>
                    <xsl:text>&#10;  </xsl:text>
                </section>
            </xsl:for-each>
            <xsl:text>&#10;</xsl:text>
        </bundle>
        <xsl:text>&#10;</xsl:text>
    </xsl:template>
</xsl:stylesheet>
