<?xml version="1.0" encoding="UTF-8"?>
<!--
     weave.xsl - make one XML snapshot of an lp5 article tree.

     Example (run from the repository root):
       xsltproc -o weave.xml weave.xsl lp5.lp5/lp5.lp5

     The result is an index for source-navigation tools, not tangled output.
     Each article is emitted in preorder, with the root article first. Article
     IDs are filenames, and code sections are grouped by bundle name so
     callers can find each bundle.
     Code text and lp5-* reference
     elements retain their original order and content.

     The input file is the root article. Its directory is the base for
     document() lookups, so no directory parameter is needed. This first pass
     uses this repository's convention that the root article is lp5.lp5 and
     the root bundle is unnamed.

     Article validation is imported from tangle.xsl so both transforms apply
     the same on-disk format rules to each article that exists. Missing child
     articles remain explicit unresolved links in the index.
-->
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:exsl="http://exslt.org/common"
    extension-element-prefixes="exsl">

    <!-- Reuse the shared article validator and path helper from the tangle. -->
    <xsl:import href="tangle.xsl"/>

    <!-- Override tangle.xsl's HTML output method for this XML result. -->
    <!-- Do not pretty-print: serializer-inserted whitespace could alter code. -->
    <xsl:output method="xml" encoding="UTF-8" indent="no"/>

    <xsl:template match="/">
        <!-- Fail before writing the index if any reachable article is invalid. -->
        <xsl:call-template name="validate-weave-tree">
            <xsl:with-param name="document" select="."/>
            <xsl:with-param name="location" select="'lp5.lp5'"/>
            <xsl:with-param name="visited" select="'|'"/>
        </xsl:call-template>

        <lp5-weave version="1">
            <!-- Article order is preorder, so the first article is the root. -->
            <xsl:text>&#10;  </xsl:text>
            <xsl:variable name="article-records">
                <articles>
                    <xsl:call-template name="emit-articles">
                        <xsl:with-param name="document" select="."/>
                        <xsl:with-param name="location" select="'lp5.lp5'"/>
                        <xsl:with-param name="visited" select="'|'"/>
                    </xsl:call-template>
                    <xsl:text>&#10;  </xsl:text>
                </articles>
            </xsl:variable>
            <xsl:copy-of select="exsl:node-set($article-records)/articles"/>

            <!-- Build a lookup list from bundle names to their code sections. -->
            <xsl:text>&#10;  </xsl:text>
            <bundles>
                <!-- EXSLT node-set lets XSLT 1.0 group the emitted records. -->
                <xsl:for-each select="exsl:node-set($article-records)/articles/article/section[@data-lp5-kind='code']">
                    <xsl:variable name="bundle-name" select="normalize-space(name)"/>
                    <xsl:if test="not(preceding::section[@data-lp5-kind='code'][normalize-space(name) = $bundle-name])">
                        <xsl:text>&#10;    </xsl:text>
                        <bundle name="{$bundle-name}">
                            <xsl:for-each select="exsl:node-set($article-records)/articles/article/section[@data-lp5-kind='code'][normalize-space(name) = $bundle-name]">
                                <xsl:text>&#10;      </xsl:text>
                                <section article="{../@file}"/>
                            </xsl:for-each>
                            <xsl:text>&#10;    </xsl:text>
                        </bundle>
                    </xsl:if>
                </xsl:for-each>
                <xsl:text>&#10;  </xsl:text>
            </bundles>
            <xsl:text>&#10;</xsl:text>
        </lp5-weave>
        <xsl:text>&#10;</xsl:text>
    </xsl:template>

    <!--
         Validate each reachable article that exists. A missing child is useful
         source information too, so warn about it and let the weave record the
         unresolved child link instead of aborting the entire transform.
    -->
    <xsl:template name="validate-weave-tree">
        <xsl:param name="document"/>
        <xsl:param name="location"/>
        <xsl:param name="visited"/>

        <xsl:if test="not(contains($visited, concat('|', $location, '|'))) and $document/*">
            <xsl:call-template name="validate-article">
                <xsl:with-param name="document" select="$document"/>
                <xsl:with-param name="location" select="$location"/>
            </xsl:call-template>
            <xsl:for-each select="$document/template/children/li">
                <xsl:variable name="child-location" select="string(@id)"/>
                <xsl:variable name="child-document" select="document(string(@id), .)"/>
                <xsl:choose>
                    <xsl:when test="$child-document/*">
                        <xsl:call-template name="validate-weave-tree">
                            <xsl:with-param name="document" select="$child-document"/>
                            <xsl:with-param name="location" select="string($child-location)"/>
                            <xsl:with-param name="visited"
                                select="concat($visited, $location, '|')"/>
                        </xsl:call-template>
                    </xsl:when>
                    <xsl:otherwise>
                        <xsl:message>
                            <xsl:text>Warning: article '</xsl:text>
                            <xsl:value-of select="$child-location"/>
                            <xsl:text>' is linked but unavailable.</xsl:text>
                        </xsl:message>
                    </xsl:otherwise>
                </xsl:choose>
            </xsl:for-each>
        </xsl:if>
    </xsl:template>

    <!--
         Write one flat article record, then recurse through its child links.
         The visited path protects against cycles while allowing the same
         article to appear again if the source tree is a DAG rather than a tree.
    -->
    <xsl:template name="emit-articles">
        <xsl:param name="document"/>
        <xsl:param name="location"/>
        <xsl:param name="visited"/>

        <xsl:if test="not(contains($visited, concat('|', $location, '|')))" >
            <xsl:text>&#10;    </xsl:text>
            <article file="{$location}">
                <!-- Preserve source order, leaving each section's contents intact. -->
                <xsl:for-each select="$document/template/heading |
                        $document/template/section[@data-lp5-kind='explanation'] |
                        $document/template/section[@data-lp5-kind='code']">
                    <xsl:text>&#10;      </xsl:text>
                    <xsl:copy-of select="."/>
                </xsl:for-each>

                <!-- Child IDs are filenames relative to the article directory. -->
                <xsl:text>&#10;      </xsl:text>
                <children>
                    <xsl:for-each select="$document/template/children/li">
                        <xsl:variable name="child-document" select="document(string(@id), .)"/>
                        <xsl:text>&#10;        </xsl:text>
                        <child>
                            <xsl:attribute name="file"><xsl:value-of select="@id"/></xsl:attribute>
                            <xsl:attribute name="status">
                                <xsl:choose>
                                    <xsl:when test="$child-document/*">available</xsl:when>
                                    <xsl:otherwise>missing</xsl:otherwise>
                                </xsl:choose>
                            </xsl:attribute>
                        </child>
                    </xsl:for-each>
                    <xsl:if test="$document/template/children/li">
                        <xsl:text>&#10;      </xsl:text>
                    </xsl:if>
                </children>
                <xsl:text>&#10;    </xsl:text>
            </article>

            <!-- Visit child articles in the exact order given by <children>. -->
            <xsl:for-each select="$document/template/children/li">
                <xsl:variable name="child-location" select="string(@id)"/>
                <xsl:variable name="child-document" select="document(string(@id), .)"/>
                <xsl:if test="$child-document/*">
                    <xsl:call-template name="emit-articles">
                        <xsl:with-param name="document" select="$child-document"/>
                        <xsl:with-param name="location" select="string($child-location)"/>
                        <xsl:with-param name="visited"
                            select="concat($visited, $location, '|')"/>
                    </xsl:call-template>
                </xsl:if>
            </xsl:for-each>
        </xsl:if>
    </xsl:template>


</xsl:stylesheet>
